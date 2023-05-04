from os.path import exists
from typing import Any, List, Mapping, Optional, Self, Set, MutableMapping

from syncify.local.files.track.collection.processor import TrackProcessor
from syncify.local.files.track.collection.compare import TrackCompare
from syncify.local.files.track.base import Track


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
    :param library_folder: Full path of parent folder containing all tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    def __init__(
            self,
            comparators: Optional[List[TrackCompare]] = None,
            match_all: bool = True,
            include_paths: Optional[Set[str]] = None,
            exclude_paths: Optional[Set[str]] = None,
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None,
    ):
        self.comparators = comparators
        self.match_all = match_all

        self.include_paths: Optional[Set[str]] = include_paths
        self.exclude_paths: Optional[Set[str]] = exclude_paths

        self.library_folder = None
        self.original_folder: Optional[str] = None
        self.sanitise_file_paths(library_folder=library_folder, other_folders=other_folders)

    def sanitise_file_paths(
            self, library_folder: Optional[str] = None, other_folders: Optional[Set[str]] = None
    ) -> None:
        """
        Assign library folder and attempt to sanitise given include/exclude file paths
        based on other possible folder stems.

        :param library_folder: Full path of parent folder containing all tracks.
        :param other_folders: Full paths of other possible library paths.
            Use to replace path stems from other libraries for the paths in loaded playlists.
            Useful when managing similar libraries on multiple platforms.
        """
        self.library_folder = library_folder
        self.original_folder: Optional[str] = None
        self._check_for_other_folder_stem(other_folders, self.include_paths, self.exclude_paths)

        if self.include_paths is not None:
            self.include_paths = {self._sanitise_file_path(path) for path in self.include_paths}
            self.include_paths = {path for path in self.include_paths if path is not None}

        if self.exclude_paths is not None:
            self.exclude_paths = {self._sanitise_file_path(path) for path in self.exclude_paths}
            self.exclude_paths = {path for path in self.exclude_paths if path is not None}

    def _check_for_other_folder_stem(self, stems: Optional[List[str]], *paths: Optional[List[str]]) -> None:
        """
        Checks for the presence of some other folder as the stem of one of the given paths.
        Useful when managing similar libraries across multiple operating systems.

        :param stems: Full paths of possible stems.
        :param paths: Paths to search through for a match.
        """
        if stems is None:
            return

        self.original_folder = None

        for paths_list in paths:
            if paths_list is None:
                continue

            for path in paths_list:
                results = [stem for stem in stems if path.startswith(stem)]
                if len(results) != 0:
                    self.original_folder = results[0]
                    break

    def _sanitise_file_path(self, path: Optional[str]) -> Optional[str]:
        """
        Sanitise a file path by:
            - replacing path stems found in other_folders
            - sanitising path separators to match current os separator
            - checking the track exists and replacing path with case-sensitive path if found

        :param path: Path to sanitise.
        :return: Sanitised path if path exists, None if not.
        """
        if not path:
            return

        if self.library_folder is not None:
            # check if replacement of filepath stem is necessary
            if self.original_folder is not None:
                path = path.replace(self.original_folder, self.library_folder)

            # sanitise path separators
            path = path.replace("\\", "/") if "/" in self.library_folder else path.replace("/", "\\")

        if exists(path):
            return path

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        source = xml["SmartPlaylist"]["Source"]

        match_all: bool = source["Conditions"]["@CombineMethod"] == "All"

        # tracks to include even if they don't meet match conditions
        include_str: str = source.get("ExceptionsInclude")
        include: Optional[List[str]] = include_str.split("|") if isinstance(include_str, str) else None

        # tracks to exclude even if they do meet match conditions
        exclude_str: str = source.get("Exceptions")
        exclude: Optional[List[str]] = exclude_str.split("|") if isinstance(exclude_str, str) else None

        comparators: List[TrackCompare] = TrackCompare.from_xml(xml=xml)

        return cls(comparators=comparators, match_all=match_all, include_paths=include, exclude_paths=exclude)

    def match(self, tracks: List[Track], reference: Optional[Track] = None):
        """
        Return a new list of tracks from input tracks that match the given conditions.

        :param tracks: List of tracks to search through for matches.
        :param reference: Optional reference track to use when comparator has no expected value.
        :return: List of tracks that match the conditions.
        """
        if self.comparators is None or len(self.comparators) == 0:
            return []

        matches = []
        for track in tracks:
            if self.exclude_paths and track.path in self.exclude_paths:
                continue
            elif self.include_paths and track.path in self.include_paths:
                matches.append(track)
                continue

            match_results = []
            for comparator in self.comparators:
                if comparator.expected is None:
                    match_results.append(comparator.compare(track_1=track, track_2=reference))
                else:
                    match_results.append(comparator.compare(track_1=track))

            if self.match_all and all(match_results):
                matches.append(track)
            elif not self.match_all and any(match_results):
                matches.append(track)

        return matches

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "library_folder": self.library_folder,
            "original_folder": self.original_folder,
            "include": self.include_paths,
            "exclude": self.exclude_paths,
            "match_all": self.match_all,
            "comparators": self.comparators
        }
