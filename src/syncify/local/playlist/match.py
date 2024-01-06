from collections.abc import Collection, Mapping, Sequence, Iterable, Callable
from dataclasses import dataclass, field
from os.path import exists
from typing import Any, Self

from syncify.shared.core.enums import Fields
from syncify.shared.core.misc import Result
from syncify.local.track import LocalTrack
from syncify.processors.base import MusicBeeProcessor
from syncify.processors.compare import Comparer
from syncify.processors.sort import ItemSorter
from syncify.shared.types import UnitSequence, UnitCollection
from syncify.shared.utils import to_collection


@dataclass(frozen=True)
class MatchResult(Result):
    """
    Results from matching a collection of tracks to a set of conditions.

    :ivar include: Sequence of LocalTracks that matched include settings.
    :ivar exclude: Sequence of LocalTracks that matched exclude settings.
    :ivar compare: Sequence of LocalTracks that matched :py:class:`ItemComparer` settings
    """
    include: Sequence[LocalTrack] = field(default=tuple())
    exclude: Sequence[LocalTrack] = field(default=tuple())
    compare: Sequence[LocalTrack] = field(default=tuple())


class LocalMatcher(MusicBeeProcessor):
    """
    Get matches for local tracks based on given comparers.

    :param comparers: List of comparers to compare a list of tracks against.
        When None, returns all tracks unless include_paths or exclude_paths are defined.
    :param match_all: If True, the track must match all comparers to be valid.
        If False, match any of comparers i.e. only one match needed to be valid.
        Ignored when comparers equal None.
    :param include_paths: List of paths for tracks to include regardless of comparer matches.
    :param exclude_paths: List of paths for tracks to exclude regardless of comparer matches.
    :param existing_paths: List of existing paths on the file system.
        Used when sanitising paths to perform case-sensitive path replacement.
    :param library_folder: Absolute path of the folder containing all tracks.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param check_existence: Check for the existence of the file paths on the file system
        when sanitising the given paths and reject any that don't.
    """

    __slots__ = ("comparers", "match_all", "include_paths", "exclude_paths", "library_folder", "original_folder",)

    @classmethod
    def from_xml(
            cls,
            xml: Mapping[str, Any],
            library_folder: str | None = None,
            other_folders: UnitCollection[str] = (),
            existing_paths: Iterable[str] = (),
            check_existence: bool = True,
            **__
    ) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        :param library_folder: Absolute path of the folder containing all tracks.
        :param other_folders: Absolute paths of other possible library paths.
            Use to replace path stems from other libraries for the paths in loaded playlists.
            Useful when managing similar libraries on multiple platforms.
        :param existing_paths: List of existing paths on the file system.
            Used when sanitising paths to perform case-sensitive path replacement.
        :param check_existence: Check for the existence of the file paths on the file system
            when sanitising the given paths and reject any that don't.
        """
        source = xml["SmartPlaylist"]["Source"]

        match_all: bool = source["Conditions"]["@CombineMethod"] == "All"

        # tracks to include even if they don't meet match conditions
        include_str: str = source.get("ExceptionsInclude")
        include = set(include_str.split("|")) if isinstance(include_str, str) else ()

        # tracks to exclude even if they do meet match conditions
        exclude_str: str = source.get("Exceptions")
        exclude = set(exclude_str.split("|")) if isinstance(exclude_str, str) else ()

        comparers: Sequence[Comparer] = Comparer.from_xml(xml=xml)

        if len(comparers) == 1:
            # when user has not set an explicit comparer, there will still be an 'allow all' comparer
            # check for this 'allow all' comparer and remove if present to speed up comparisons
            c = comparers[0]
            if "contains" in c.condition.casefold() and len(c.expected) == 1 and not c.expected[0]:
                comparers = ()

        return cls(
            comparers=comparers or (),
            match_all=match_all,
            include_paths=include,
            exclude_paths=exclude,
            existing_paths=existing_paths,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=check_existence
        )

    def __init__(
            self,
            comparers: UnitSequence[Comparer] = (),
            match_all: bool = True,
            include_paths: Collection[str] = (),
            exclude_paths: Collection[str] = (),
            existing_paths: Iterable[str] = (),
            library_folder: str | None = None,
            other_folders: UnitCollection[str] = (),
            check_existence: bool = True,
    ):
        self.comparers: tuple[Comparer, ...] = to_collection(comparers)
        self.match_all = match_all

        self.include_paths: Collection[str] = include_paths
        self.exclude_paths: Collection[str] = exclude_paths
        self.existing_paths: Mapping[str, str] = {path.casefold(): path for path in existing_paths}

        self.library_folder = library_folder.rstrip("\\/") if library_folder is not None else library_folder
        self.original_folder: str | None = None
        self.sanitise_file_paths(*to_collection(other_folders), check_existence=check_existence)

    def sanitise_file_paths(self, *other_folders: str, check_existence: bool = True) -> None:
        """
        Attempt to sanitise include/exclude file paths stored in this object
        based on currently stored library folder and other possible folder stems.

        :param other_folders: Absolute paths of other possible library paths.
            Use to replace path stems from other libraries for the paths in loaded playlists.
            Useful when managing similar libraries on multiple platforms.
        :param check_existence: Check for the existence of the file paths on the file system.
        """
        if self.library_folder and other_folders and self.original_folder is None:
            # determine original_folder from other_folders using include/exclude paths
            self._check_for_other_folder_stem(other_folders, *self.include_paths, *self.exclude_paths)

        exclude = []
        for path in self.exclude_paths:
            path = self.sanitise_file_path(path, check_existence=check_existence)
            if path is not None:
                exclude.append(path.casefold())

        include = []
        for path in self.include_paths:
            path = self.sanitise_file_path(path, check_existence=check_existence)
            if path is not None and (len(exclude) == 0 or path.casefold() not in exclude):
                include.append(path.casefold())

        self.exclude_paths = exclude
        self.include_paths = include

    def _check_for_other_folder_stem(self, stems: Iterable[str], *paths: str | None) -> None:
        """
        Checks for the presence of some other folder as the stem of one of the given paths.
        Useful when managing similar libraries across multiple operating systems.

        :param stems: Absolute paths of possible stems.
        :param paths: Paths to search through for a match.
        """
        stems = tuple(folder.rstrip("\\/") for folder in stems if folder is not None)
        self.original_folder = None
        if not stems:
            return

        for path in paths:
            if path is None:
                continue

            result = next((stem for stem in stems if path.casefold().startswith(stem.casefold())), None)
            if result:
                self.original_folder = result
                break

    def sanitise_file_path(self, path: str | None, check_existence: bool = True) -> str | None:
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
            if self.library_folder is not None:
                seps = ("\\", "/") if "/" in self.library_folder else ("/", "\\")
                path = path.replace(*seps)

        path = self.existing_paths.get(path.casefold(), path)

        if not check_existence or exists(path):
            return path

    def __call__(
            self, tracks: Collection[LocalTrack], reference: LocalTrack | None = None, combine: bool = True
    ) -> list[LocalTrack] | MatchResult:
        return self.match(tracks=tracks, reference=reference, combine=combine)

    def match(
            self, tracks: Collection[LocalTrack], reference: LocalTrack | None = None, combine: bool = True
    ) -> list[LocalTrack] | MatchResult:
        """
        Return a new list of tracks from input tracks that match the given conditions.

        :param tracks: List of tracks to search through for matches.
        :param reference: Optional reference track to use when comparer has no expected value.
        :param combine: If True, return one list of all tracks. If False, return tuple of 3 lists.
        :return: If ``combine`` is True, list of tracks that match the conditions.
            If ``combine`` is False, return :py:class:`MatchResult`
        """
        if len(tracks) == 0:  # skip match
            return [] if combine else MatchResult()

        path_tracks: Mapping[str, LocalTrack] = {track.path.casefold(): track for track in tracks}

        include: list[LocalTrack] = [path_tracks[path] for path in self.include_paths if path in path_tracks]
        exclude: list[LocalTrack] = [path_tracks[path] for path in self.exclude_paths if path in path_tracks]

        if not self.comparers:  # skip comparer checks
            if not self.include_paths:
                include = list(tracks)
            if combine:
                return [track for track in include if track not in exclude]
            return MatchResult(include=include, exclude=exclude)

        compared: list[LocalTrack] = []
        for track in tracks:  # run comparer checks
            match_results = []
            for comparer in self.comparers:
                if comparer.expected is None:  # compare with a reference
                    match_results.append(comparer.compare(item=track, reference=reference))
                else:  # compare with the comparers expected values
                    match_results.append(comparer.compare(item=track))

            if self.match_all and all(match_results):
                compared.append(track)
            elif not self.match_all and any(match_results):
                compared.append(track)

        if combine:
            compared_reduced = {track for track in compared if track not in include}
            return [track for results in [compared_reduced, include] for track in results if track not in exclude]
        return MatchResult(include=include, exclude=exclude, compare=compared)

    def to_xml(
            self,
            tracks: list[LocalTrack],
            tracks_original: list[LocalTrack],
            path_mapper: Callable[[Collection[str]], Collection[str]] = lambda x: x,
            **__
    ) -> Mapping[str, Any]:
        """
        Export this object's settings to a map ready for export to an XML playlist file.

        :param tracks: The tracks to export.
        :param tracks_original: The original tracks this playlist held when loading from the file.
        :param path_mapper: A mapper to apply for paths before formatting to a string value for the XML-like output.
        :return: A map representing the values to be exported to the XML playlist file.
        """
        output_path_map: Mapping[str, LocalTrack] = {track.path.casefold(): track for track in tracks}

        if self.comparers:
            # match again on current conditions to check for differences from original list
            # this ensures that the paths included in the XML output
            # do not include paths that match any of the conditions in the comparers

            # copy the list of tracks as the sorter will modify the list order
            tracks_original = tracks_original.copy()
            # get the last played track as reference in case comparer is looking for the playing tracks as reference
            ItemSorter.sort_by_field(tracks_original, field=Fields.LAST_PLAYED, reverse=True)
            matches: MatchResult = self(tracks_original, reference=tracks_original[0], combine=False)
            compared_path_map: Mapping[str, LocalTrack] = {track.path.casefold(): track for track in matches.compare}

            # get new include/exclude paths based on the leftovers after matching on comparers
            self.include_paths = list(output_path_map - compared_path_map.keys())
            self.exclude_paths = list(compared_path_map.keys() - output_path_map)
        else:
            compared_path_map = output_path_map

        # get the track objects related to these paths and their actual paths as stored in their objects
        include_tracks: tuple[LocalTrack | None, ...] = tuple(output_path_map.get(p) for p in self.include_paths)
        exclude_tracks: tuple[LocalTrack | None, ...] = tuple(compared_path_map.get(p) for p in self.exclude_paths)
        include_paths: tuple[str, ...] = tuple(track.path for track in include_tracks if track is not None)
        exclude_paths: tuple[str, ...] = tuple(track.path for track in exclude_tracks if track is not None)

        xml = {}
        if len(include_paths) > 0:  # assign include paths to XML object
            xml["ExceptionsInclude"] = "|".join(path_mapper(include_paths))
        if len(exclude_paths) > 0:  # assign exclude paths to XML object
            xml["Exceptions"] = "|".join(path_mapper(exclude_paths))

        return xml

    def as_dict(self):
        return {
            "include": self.include_paths,
            "exclude": self.exclude_paths,
            "library_folder": self.library_folder,
            "original_folder": self.original_folder,
            "match_all": self.match_all,
            "comparers": self.comparers,
        }
