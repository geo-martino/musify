from __future__ import annotations

import logging
from abc import ABCMeta
from collections.abc import Collection, Mapping, Sequence, Iterable, Callable
from dataclasses import dataclass, field
from os.path import exists
from typing import Any

from syncify.local.file import File
from syncify.local.track import LocalTrack
from syncify.processors.base import Filter, MusicBeeProcessor
from syncify.processors.compare import Comparer
from syncify.processors.sort import ItemSorter
from syncify.shared.core.base import NamedObject
from syncify.shared.core.enum import Fields
from syncify.shared.core.misc import Result
from syncify.shared.logger import SyncifyLogger
from syncify.shared.types import UnitCollection
from syncify.shared.utils import to_collection


class FilterDefinedList[T: str | NamedObject](Filter[T], Collection[T]):

    @property
    def ready(self):
        return len(self.values) > 0

    def __init__(self, values: Collection[T] = (), *_, **__):
        self.values: Collection[T] = values

    def __call__(self, values: Collection[T] | None = None, *_, **__) -> Collection[T]:
        return self.process(values=values)

    def process(self, values: Collection[T] | None = None, *_, **__) -> Collection[T]:
        """Returns all ``values`` that match this filter's settings"""
        if self.ready:
            matches = [value for value in values if self.transform(value) in self.values]
            if isinstance(self.values, Sequence):
                matches = sorted((self.values.index(self.transform(match)), match) for match in matches)
                return [match[1] for match in matches]
            return matches
        return values

    def as_dict(self) -> dict[str, Any]:
        return {"values": self.values}

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __contains__(self, item: Any):
        return item in self.values


class FilterPath[T: str | File](FilterDefinedList[T]):

    def __init__(
            self,
            values: Collection[T] = (),
            stem_replacement: str | None = None,
            possible_stems: UnitCollection[str] = (),
            existing_paths: Iterable[str] = (),
            check_existence: bool = True,
            *_,
            **__
    ):
        super().__init__(values)
        self.stem_original: str | None = None
        self.stem_replacement = stem_replacement
        self.possible_stems = tuple(stem.rstrip("\\/") for stem in to_collection(possible_stems) if stem is not None)
        self.existing_paths: Mapping[str, str] = {path.casefold(): path for path in existing_paths}

        if not self.values:
            return

        # determine original_stem from possible_stems using given values
        for path in self.values:
            if path is None:
                continue

            self.stem_original = next((
                stem for stem in self.possible_stems if path.casefold().startswith(stem.casefold())
            ), None)
            if self.stem_original:
                break

        paths = []
        for path in self.values:
            path = self.transform(path, check_existence=check_existence)
            if path:
                paths.append(path)

        self.values = paths

    def transform(self, value: T | None, check_existence: bool = False) -> str | None:
        """
        Sanitise a file path by:
            - replacing any paths with ``original_stem`` with ``replacement_stem``
            - sanitising path separators to match current OS separator
            - replacing path with case-sensitive path if found in ``existing_paths``

        :param value: Path of :py:class:`File` with a path to sanitise.
        :param check_existence: Check for the existence of the file path on the file system.
        :return: Sanitised path if path exists, None if not.
        """
        if not value:
            return
        path = value.path if isinstance(value, File) else value

        if self.stem_replacement is not None:
            for stem in self.possible_stems:
                path = path.replace(stem, self.stem_replacement)

            # sanitise path separators
            path = path.replace("//", "/").replace("\\\\", "\\")
            if self.stem_replacement is not None:
                seps = ("\\", "/") if "/" in self.stem_replacement else ("/", "\\")
                path = path.replace(*seps)

        path = self.existing_paths.get(path.casefold(), path)
        if not check_existence or exists(path):
            return path.casefold()

    def as_dict(self) -> dict[str, Any]:
        return {
            "values": self.values,
            "original_stem": self.stem_original,
            "replacement_stem": self.stem_replacement,
            "existing_paths": self.existing_paths,
        }


class FilterComparers[T: str | NamedObject](Filter[T]):

    @property
    def ready(self):
        return len(self.comparers) > 0

    def __init__(self, comparers: Collection[Comparer] = (), match_all: bool = True, *_, **__):
        self.comparers: Collection[Comparer] = comparers
        self.match_all: bool = match_all

    def __call__(self, values: Collection[T], reference: T | None = None, *_, **__) -> Collection[T]:
        return self.process(values=values, reference=reference)

    def process(self, values: Collection[T], reference: T | None = None, *_, **__) -> Collection[T]:
        if not self.ready:
            return values

        def run_comparer(c: Comparer, v: T) -> bool:
            """Run the comparer ``c`` for the given value ``v``"""
            return c(self.transform(v), reference=reference) if c.expected is None else c(self.transform(v))

        if self.match_all:
            for comparer in self.comparers:
                values = [value for value in values if run_comparer(comparer, value)]
            return values

        matches = []
        for comparer in self.comparers:
            matches.extend(value for value in values if run_comparer(comparer, value) and value not in matches)
        return matches

    def as_dict(self) -> dict[str, Any]:
        return {"comparers": self.comparers, "match_all": self.match_all}


###########################################################################
## Composites
###########################################################################
class FilterComposite[T](Filter[T], Collection[Filter], metaclass=ABCMeta):

    @property
    def ready(self):
        return any(filter_.ready for filter_ in self.filters)

    def __init__(self, *filters: Filter[T], **__):
        self.filters = filters

    def __iter__(self):
        def flat_filter_list(fltr: Filter | Collection[Filter]) -> Iterable[Filter]:
            """
            Get flat list of all :py:class:`Filter` objects in the given Filter,
            flattening out any :py:class:`FilterComposite` objects
            """
            if isinstance(fltr, FilterComposite):
                return iter(fltr)
            return [fltr]
        return (f for filter_ in self.filters for f in flat_filter_list(filter_))

    def __len__(self):
        return len(self.filters)

    def __contains__(self, item: Any):
        return item in self.filters


class FilterIncludeExclude[T: Any, U: Filter, V: Filter](FilterComposite[T]):

    def __init__(self, include: U, exclude: V, *_, **__):
        super().__init__(include, exclude)
        self.include: U = include
        self.exclude: V = exclude

    def __call__(self, values: Collection[T], *_, **__) -> list[T]:
        return self.process(values=values)

    def process(self, values: Collection[T], *_, **__) -> list[T]:
        """Filter down ``values`` that match this filter's settings from"""
        values = self.include.process(values) if self.include.ready else values
        exclude = self.exclude.process(values) if self.exclude.ready else ()
        return [v for v in values if v not in exclude]

    def as_dict(self) -> dict[str, Any]:
        return {"include": self.include, "exclude": self.exclude}


@dataclass(frozen=True)
class MatchResult[T: Any](Result):
    """
    Results from :py:class:`FilterMatcher` separated by individual filter results.

    :ivar included: Sequence of LocalTracks that matched include settings.
    :ivar excluded: Sequence of LocalTracks that matched exclude settings.
    :ivar compared: Sequence of LocalTracks that matched :py:class:`ItemComparer` settings
    """
    included: Collection[T] = field(default=tuple())
    excluded: Collection[T] = field(default=tuple())
    compared: Collection[T] = field(default=tuple())

    @property
    def combined(self) -> list[T]:
        """Combine the individual results to one combined list"""
        return [track for results in [self.compared, self.included] for track in results if track not in self.excluded]


class FilterMatcher[T: Any, U: Filter, V: Filter, X: FilterComparers](MusicBeeProcessor, FilterComposite[T]):
    """
    Get matches for items based on given filters.

    :param include: A Filter for simple include comparisons to use when matching.
    :param exclude: A Filter for simple exclude comparisons to use when matching.
    :param comparers: A Filter for fine-grained comparisons to use when matching.
        When not given or the given Filter if not ready,
        returns all given values on match unless include or exclude are defined and ready.
    """

    __slots__ = ("comparers", "include", "exclude")

    @classmethod
    def from_xml(
            cls,
            xml: Mapping[str, Any],
            library_folder: str | None = None,
            other_folders: UnitCollection[str] = (),
            existing_paths: Iterable[str] = (),
            check_existence: bool = True,
            **__
    ) -> FilterMatcher[T, FilterPath[T], FilterPath[T], FilterComparers[T]]:
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
            include=FilterPath(
                values=include,
                stem_replacement=library_folder,
                possible_stems=other_folders,
                existing_paths=existing_paths,
                check_existence=check_existence
            ),
            exclude=FilterPath(
                values=exclude,
                stem_replacement=library_folder,
                possible_stems=other_folders,
                existing_paths=existing_paths,
                check_existence=check_existence
            ),
            comparers=FilterComparers(comparers, match_all=match_all),
        )

    def to_xml(
            self,
            tracks: list[LocalTrack],
            tracks_original: list[LocalTrack],
            path_mapper: Callable[[Collection[str]], Collection[str]] = lambda x: x,
            **__
    ) -> Mapping[str, Any]:
        """
        Export this object's include and exclude filters to a map ready for export to an XML playlist file.

        :param tracks: The tracks to export.
        :param tracks_original: The original tracks matched from the settings in the original file.
        :param path_mapper: A mapper to apply for paths before formatting to a string value for the XML-like output.
        :return: A map representing the values to be exported to the XML playlist file.
        """
        if not isinstance(self.include, FilterDefinedList) and not isinstance(self.exclude, FilterDefinedList):
            self.logger.warning(
                "Cannot export this filter to XML: Include and Exclude settings must both be list filters"
            )
            return {}

        output_path_map: Mapping[str, LocalTrack] = {track.path.casefold(): track for track in tracks}

        if self.comparers:
            # match again on current conditions to check for differences from original list
            # this ensures that the paths included in the XML output
            # do not include paths that match any of the conditions in the comparers

            # copy the list of tracks as the sorter will modify the list order
            tracks_original = tracks_original.copy()
            # get the last played track as reference in case comparer is looking for the playing tracks as reference
            ItemSorter.sort_by_field(tracks_original, field=Fields.LAST_PLAYED, reverse=True)

            compared_path_map = {
                track.path.casefold(): track for track in self.comparers(tracks_original, reference=tracks_original[0])
            } if self.comparers.ready else {}

            # get new include/exclude paths based on the leftovers after matching on comparers
            self.exclude.values = list(compared_path_map.keys() - output_path_map)
            self.include.values = [v for v in list(output_path_map - compared_path_map.keys()) if v not in self.exclude]
        else:
            compared_path_map = output_path_map

        # get the track objects related to these paths and their actual paths as stored in their objects
        include_tracks: tuple[LocalTrack | None, ...] = tuple(output_path_map.get(p) for p in self.include)
        exclude_tracks: tuple[LocalTrack | None, ...] = tuple(compared_path_map.get(p) for p in self.exclude)
        include_paths: tuple[str, ...] = tuple(track.path for track in include_tracks if track is not None)
        exclude_paths: tuple[str, ...] = tuple(track.path for track in exclude_tracks if track is not None)

        xml = {}
        if len(include_paths) > 0:  # assign include paths to XML object
            xml["ExceptionsInclude"] = "|".join(path_mapper(include_paths))
        if len(exclude_paths) > 0:  # assign exclude paths to XML object
            xml["Exceptions"] = "|".join(path_mapper(exclude_paths))

        return xml

    def __init__(
            self,
            include: U = FilterDefinedList(),
            exclude: V = FilterDefinedList(),
            comparers: X = FilterComparers(),
            *_,
            **__
    ):
        super().__init__(comparers, include, exclude)
        # noinspection PyTypeChecker
        self.logger: SyncifyLogger = logging.getLogger(__name__)

        self.comparers = comparers
        self.include = include
        self.exclude = exclude

    def __call__(self, values: Collection[T], reference: T | None = None, *_, **__) -> list[T]:
        return self.process(values=values, reference=reference)

    def process(self, values: Collection[T], reference: T | None = None, *_, **__) -> list[T]:
        """
        Return a new, filtered list of items from input ``values`` that match the stored filters.

        :param values: List of items to filter.
        :param reference: Optional reference track to use when filtering on
            comparers and the comparer has no expected value.
        :return: List of items that match the conditions.
        """
        return self.process_to_result(values=values, reference=reference).combined

    def process_to_result(self, values: Collection[T], reference: T | None = None, *_, **__) -> MatchResult:
        """Same as :py:meth:`process` but returns the results of each filter to a :py:class`MatchResult` object"""
        if len(values) == 0:  # skip match
            return MatchResult()

        included = self.include(values)
        excluded = self.exclude(values) if self.exclude.ready else ()
        tracks_reduced = {track for track in values if track not in included}
        compared = self.comparers(tracks_reduced, reference=reference) if self.comparers.ready else ()

        return MatchResult(included=included, excluded=excluded, compared=compared)

    def as_dict(self):
        return {"include": self.include, "exclude": self.exclude, "comparers": self.comparers}
