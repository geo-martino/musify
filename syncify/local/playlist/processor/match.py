from dataclasses import dataclass
from os.path import exists
from typing import Any, List, Mapping, Optional, Self, Collection, Union, Set

from syncify.local.playlist.processor.base import TrackProcessor
from syncify.local.playlist.processor.compare import TrackCompare
from syncify.local.track import LocalTrack
from syncify.utils import UnionList, make_list


@dataclass
class MatchResult:
    """Results from matching a collection of tracks to a set of conditions."""
    include: List[LocalTrack]
    exclude: List[LocalTrack]
    compared: List[LocalTrack]


class TrackMatch(TrackProcessor):
    """
    Get matches for tracks based on given comparators.

    :param comparators: List of comparators to compare a list of tracks against.
        When None, returns all tracks unless include_paths or exclude_paths are defined.
    :param match_all: If True, the track must match all comparators to be valid.
        If False, match any of comparators i.e. only one match needed to be valid.
        Ignored when comparators equal None.
    :param include_paths: List of paths for tracks to include regardless of comparator matches.
    :param exclude_paths: List of paths for tracks to exclude regardless of comparator matches.
    :param library_folder: Absolute path of the folder containing all tracks.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param check_existence: Check for the existence of the file paths on the file system
        when sanitising the given paths and reject any that don't.
    """

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        source = xml["SmartPlaylist"]["Source"]

        match_all: bool = source["Conditions"]["@CombineMethod"] == "All"

        # tracks to include even if they don't meet match conditions
        include_str: str = source.get("ExceptionsInclude")
        include: Optional[Set[str]] = set(include_str.split("|")) if isinstance(include_str, str) else None

        # tracks to exclude even if they do meet match conditions
        exclude_str: str = source.get("Exceptions")
        exclude: Optional[Set[str]] = set(exclude_str.split("|")) if isinstance(exclude_str, str) else None

        comparators: Optional[List[TrackCompare]] = TrackCompare.from_xml(xml=xml)

        if len(comparators) == 1:
            c = comparators[0]
            if "contains" in c.condition.casefold() and len(c.expected) == 1 and not c.expected[0]:
                comparators = None

        return cls(
            comparators=comparators,
            match_all=match_all,
            include_paths=include,
            exclude_paths=exclude,
            check_existence=False
        )

    def __init__(
            self,
            comparators: Optional[UnionList[TrackCompare]] = None,
            match_all: bool = True,
            include_paths: Optional[List[str]] = None,
            exclude_paths: Optional[Collection[str]] = None,
            library_folder: Optional[str] = None,
            other_folders: Optional[Collection[str]] = None,
            check_existence: bool = True,
    ):
        self.comparators = make_list(comparators)
        self.match_all = match_all

        self.include_paths: Optional[List[str]] = include_paths
        self.exclude_paths: Optional[List[str]] = exclude_paths

        self.library_folder = library_folder.rstrip("\\/") if library_folder is not None else library_folder
        self.original_folder: Optional[str] = None
        self.sanitise_file_paths(other_folders=other_folders, check_existence=check_existence)

    def sanitise_file_paths(
            self, other_folders: Optional[Union[str, Collection[str]]] = None, check_existence: bool = True,
    ):
        """
        Attempt to sanitise given include/exclude file paths
        based on current library folder and other possible folder stems.

        :param other_folders: Absolute paths of other possible library paths.
            Use to replace path stems from other libraries for the paths in loaded playlists.
            Useful when managing similar libraries on multiple platforms.
        :param check_existence: Check for the existence of the file paths on the file system.
        """
        if self.library_folder is not None and other_folders is not None and self.original_folder is None:
            # determine original_folder from other_folders using include/exclude paths
            self._check_for_other_folder_stem(other_folders, self.include_paths, self.exclude_paths)

        if self.exclude_paths is not None:  # filter out exclude paths
            exclude = []
            for path in self.exclude_paths:
                path = self.sanitise_file_path(path, check_existence=check_existence)
                if path is not None:
                    exclude.append(path.lower())

            self.exclude_paths = exclude

        if self.include_paths is not None:  # include filtering
            include = []
            for path in self.include_paths:
                path = self.sanitise_file_path(path, check_existence=check_existence)
                if path is not None and (self.exclude_paths is None or path.lower() not in self.exclude_paths):
                    include.append(path.lower())

            self.include_paths = include

    def _check_for_other_folder_stem(self, stems: Union[str, Collection[str]], *paths: Optional[List[str]]):
        """
        Checks for the presence of some other folder as the stem of one of the given paths.
        Useful when managing similar libraries across multiple operating systems.

        :param stems: Absolute paths of possible stems.
        :param paths: Paths to search through for a match.
        """
        stems = {folder.rstrip("\\/") for folder in make_list(stems) if folder is not None}
        self.original_folder = None

        for paths_list in paths:
            if paths_list is None:
                continue

            for path in paths_list:
                results = [stem for stem in stems if path.casefold().startswith(stem.casefold())]
                if len(results) != 0:
                    self.original_folder = results[0]
                    break

    def sanitise_file_path(self, path: Optional[str], check_existence: bool = True) -> Optional[str]:
        """
        Sanitise a file path by:
            - replacing path stems found in other_folders
            - sanitising path separators to match current os separator
            - checking the track exists and replacing path with case-sensitive path if found

        :param path: Path to sanitise.
        :param check_existence: Check for the existence of the file path on the file system.
        :return: Sanitised path if path exists, None if not.
        """
        if not path:
            return

        if self.library_folder is not None:
            if self.original_folder is not None:  # check if replacement of filepath stem is necessary
                path = path.replace(self.original_folder, self.library_folder).replace("//", "/").replace("\\\\", "\\")

            # sanitise path separators
            path = self.correct_path_separator(path)

        if not check_existence or exists(path):
            return path

    def correct_path_separator(self, path: str) -> str:
        """Align a paths separators with the separators in the path for the library folder"""
        if self.library_folder is not None:
            return path.replace("\\", "/") if "/" in self.library_folder else path.replace("/", "\\")
        else:
            return path

    def match(
            self, tracks: List[LocalTrack], reference: Optional[LocalTrack] = None, combine: bool = True
    ) -> Union[List[LocalTrack], MatchResult]:
        """
        Return a new list of tracks from input tracks that match the given conditions.

        :param tracks: List of tracks to search through for matches.
        :param reference: Optional reference track to use when comparator has no expected value.
        :param combine: If True, return one list of all tracks. If False, return tuple of 3 lists.
        :return: If combine=True, list of tracks that match the conditions. If combine=False, tuple of 3 lists:
            - List 1: Tracks that only match on include_paths
            - List 2: Tracks that only match on exclude_paths
            - List 3: Tracks that only match on comparators
        """
        if len(tracks) == 0:  # skip match
            return [] if combine else MatchResult(include=[], exclude=[], compared=[])

        path_tracks: Mapping[str, LocalTrack] = {track.path.lower(): track for track in tracks}

        include: List[LocalTrack] = []
        if self.include_paths:  # include filter
            include.extend([path_tracks[path] for path in self.include_paths if path in path_tracks])

        exclude: List[LocalTrack] = []
        if self.exclude_paths:  # filter out exclude paths
            exclude.extend([path_tracks[path] for path in self.exclude_paths if path in path_tracks])

        if self.comparators is None or len(self.comparators) == 0:  # skip comparator checks
            return [track for track in include if track not in exclude] if combine \
                else MatchResult(include=include, exclude=exclude, compared=[])

        compared: List[LocalTrack] = []
        for track in tracks:  # run comparator checks
            match_results = []
            for comparator in self.comparators:
                if comparator.expected is None:  # compare with a reference
                    match_results.append(comparator.compare(track=track, reference=reference))
                else:  # compare with the comparators expected values
                    match_results.append(comparator.compare(track=track))

            if self.match_all and all(match_results):
                compared.append(track)
            elif not self.match_all and any(match_results):
                compared.append(track)

        if combine:
            compared_reduced = [track for track in compared if track not in include]
            return [track for results in [compared_reduced, include] for track in results if track not in exclude]
        return MatchResult(include=include, exclude=exclude, compared=compared)

    def as_dict(self):
        return {
            "include": self.include_paths,
            "exclude": self.exclude_paths,
            "library_folder": self.library_folder,
            "original_folder": self.original_folder,
            "match_all": self.match_all,
            "comparators": self.comparators
        }
