from __future__ import annotations

import logging
from collections.abc import Collection, Mapping, Sequence, Callable
from dataclasses import field, dataclass
from typing import Any

from musify.local.file import File, PathMapper
from musify.local.track import LocalTrack
from musify.processors.base import Filter, MusicBeeProcessor, FilterComposite
from musify.processors.compare import Comparer
from musify.processors.filter import FilterComparers, FilterDefinedList
from musify.processors.sort import ItemSorter
from musify.shared.core.enum import Fields
from musify.shared.core.misc import Result
from musify.shared.logger import MusifyLogger


@dataclass(frozen=True)
class MatchResult[T: Any](Result):
    """
    Results from :py:class:`FilterMatcher` separated by individual filter results.

    :ivar included: Objects that matched include settings.
    :ivar excluded: Objects that matched exclude settings.
    :ivar compared: Objects that matched :py:class:`Comparer` settings
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

    __slots__ = ("include", "exclude", "comparers")

    @classmethod
    def from_xml(
            cls, xml: Mapping[str, Any], path_mapper: PathMapper = PathMapper(), **__
    ) -> FilterMatcher[T, FilterDefinedList[T], FilterDefinedList[T], FilterComparers[T]]:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        :param path_mapper: Optionally, provide a :py:class:`PathMapper` for paths stored in the playlist file.
            Useful if the playlist file contains relative paths and/or paths for other systems that need to be
            mapped to absolute, system-specific paths to be loaded and back again when saved.
        """
        source = xml["SmartPlaylist"]["Source"]

        # tracks to include/exclude even if they meet/don't meet match compare conditions
        include_str: str = source.get("ExceptionsInclude") or ""
        include = path_mapper.map_many(set(include_str.split("|")), check_existence=True)
        exclude_str: str = source.get("Exceptions") or ""
        exclude = path_mapper.map_many(set(exclude_str.split("|")), check_existence=True)

        comparers: Sequence[Comparer] = Comparer.from_xml(xml=xml)

        if len(comparers) == 1:
            # when user has not set an explicit comparer, there will still be an 'allow all' comparer
            # check for this 'allow all' comparer and remove if present to speed up comparisons
            c = comparers[0]
            if "contains" in c.condition.casefold() and len(c.expected) == 1 and not c.expected[0]:
                comparers = ()

        filter_include = FilterDefinedList(values=[path.casefold() for path in include])
        filter_exclude = FilterDefinedList(values=[path.casefold() for path in exclude])
        filter_compare = FilterComparers(comparers, match_all=source["Conditions"]["@CombineMethod"] == "All")

        filter_include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        filter_exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()

        return cls(include=filter_include, exclude=filter_exclude, comparers=filter_compare)

    def to_xml(
            self,
            items: list[LocalTrack],
            original: list[LocalTrack],
            path_mapper: Callable[[Collection[str | File]], Collection[str]] = lambda x: x,
            **__
    ) -> Mapping[str, Any]:
        """
        Export this object's include and exclude filters to a map ready for export to an XML playlist file.

        :param items: The items to export.
        :param original: The original items matched from the settings in the original file.
        :param path_mapper: A mapper to apply for paths before formatting to a string value for the XML-like output.
        :return: A map representing the values to be exported to the XML playlist file.
        """
        if not isinstance(self.include, FilterDefinedList) and not isinstance(self.exclude, FilterDefinedList):
            self.logger.warning(
                "Cannot export this filter to XML: Include and Exclude settings must both be list filters"
            )
            return {}

        output_path_map: Mapping[str, LocalTrack] = {item.path.casefold(): item for item in items}

        if self.comparers:
            # match again on current conditions to check for differences from original list
            # this ensures that the paths included in the XML output
            # do not include paths that match any of the conditions in the comparers

            # copy the list of tracks as the sorter will modify the list order
            original = original.copy()
            # get the last played track as reference in case comparer is looking for the playing tracks as reference
            ItemSorter.sort_by_field(original, field=Fields.LAST_PLAYED, reverse=True)

            compared_path_map = {
                item.path.casefold(): item for item in self.comparers(original, reference=original[0])
            } if self.comparers.ready else {}

            # get new include/exclude paths based on the leftovers after matching on comparers
            self.exclude.values = list(compared_path_map.keys() - output_path_map)
            self.include.values = [v for v in list(output_path_map - compared_path_map.keys()) if v not in self.exclude]
        else:
            compared_path_map = output_path_map

        include_items = tuple(output_path_map[path] for path in self.include if path in output_path_map)
        exclude_items = tuple(compared_path_map[path] for path in self.exclude if path in compared_path_map)

        xml = {}
        if len(include_items) > 0:  # assign include paths to XML object
            xml["ExceptionsInclude"] = "|".join(path_mapper(include_items))
        if len(exclude_items) > 0:  # assign exclude paths to XML object
            xml["Exceptions"] = "|".join(path_mapper(exclude_items))

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
        self.logger: MusifyLogger = logging.getLogger(__name__)

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
