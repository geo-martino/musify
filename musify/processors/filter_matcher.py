"""
Processors that filter down objects and data types based on some given configuration.
"""
from __future__ import annotations

import logging
from collections.abc import Collection, Mapping, Callable
from dataclasses import field, dataclass
from typing import Any

from musify.core.base import MusifyItem
from musify.core.enum import Fields, TagField, TagFields
from musify.core.result import Result
from musify.file.base import File
from musify.file.path_mapper import PathMapper
from musify.log.logger import MusifyLogger
from musify.processors.base import Filter, MusicBeeProcessor, FilterComposite
from musify.processors.compare import Comparer
from musify.processors.filter import FilterComparers, FilterDefinedList
from musify.processors.sort import ItemSorter
from musify.utils import to_collection


@dataclass(frozen=True)
class MatchResult[T: Any](Result):
    """Results from :py:class:`FilterMatcher` separated by individual filter results."""
    #: Objects that matched include settings.
    included: Collection[T] = field(default=tuple())
    #: Objects that matched exclude settings.
    excluded: Collection[T] = field(default=tuple())
    #: Objects that matched :py:class:`Comparer` settings
    compared: Collection[T] = field(default=tuple())
    #: Objects that matched on any group_by settings
    grouped: Collection[T] = field(default=tuple())

    @property
    def combined(self) -> list[T]:
        """Combine the individual results to one combined list"""
        return [track for track in [*self.compared, *self.included, *self.grouped] if track not in self.excluded]


class FilterMatcher[T: Any, U: Filter, V: Filter, X: FilterComparers](MusicBeeProcessor, FilterComposite[T]):
    """
    Get matches for items based on given filters.

    :param include: A Filter for simple include comparisons to use when matching.
    :param exclude: A Filter for simple exclude comparisons to use when matching.
    :param comparers: A Filter for fine-grained comparisons to use when matching.
        When not given or the given Filter is not ready,
        returns all given values on match unless include or exclude are defined and ready.
    :param group_by: Once all other filters are applied, also include all other items that match this tag type
        from the matched items for any remaining unmatched items.
    """

    __slots__ = ("include", "exclude", "comparers", "group_by")

    @classmethod
    def from_xml(
            cls, xml: Mapping[str, Any], path_mapper: PathMapper = PathMapper(), **__
    ) -> FilterMatcher[str, FilterDefinedList[str], FilterDefinedList[str], FilterComparers[str]]:
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

        conditions = xml["SmartPlaylist"]["Source"]["Conditions"]
        comparers: dict[Comparer, tuple[bool, FilterComparers]] = {}
        for condition in to_collection(conditions["Condition"]):
            if any(key in condition for key in {"And", "Or"}):
                sub_combine = "And" in condition
                sub_conditions = condition["And" if sub_combine else "Or"]
                sub_comparers = [Comparer.from_xml(sub) for sub in to_collection(sub_conditions["Condition"])]
                sub_filter = FilterComparers(
                    comparers=sub_comparers, match_all=sub_conditions["@CombineMethod"] == "All"
                )
            else:
                sub_combine = False
                sub_filter = FilterComparers()

            comparers[Comparer.from_xml(xml=condition)] = (sub_combine, sub_filter)

        if len(comparers) == 1 and not next(iter(comparers.values()))[1].ready:
            # when user has not set an explicit comparer, a single empty 'allow all' comparer is assigned
            # check for this 'allow all' comparer and remove it if present to speed up comparisons
            c = next(iter(comparers))
            if "contains" in c.condition.casefold() and len(c.expected) == 1 and not c.expected[0]:
                comparers = {}

        filter_include = FilterDefinedList(values=[path.casefold() for path in include])
        filter_exclude = FilterDefinedList(values=[path.casefold() for path in exclude])
        filter_compare = FilterComparers(comparers, match_all=conditions["@CombineMethod"] == "All")

        filter_include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        filter_exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()

        group_by_value = cls._pascal_to_snake(xml["SmartPlaylist"]["@GroupBy"])
        group_by = None if group_by_value == "track" else TagFields.from_name(group_by_value)[0]

        return cls(include=filter_include, exclude=filter_exclude, comparers=filter_compare, group_by=group_by)

    def to_xml(
            self,
            items: list[File],
            original: list[File | MusifyItem],
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

        items_mapped: Mapping[str, File] = {item.path.casefold(): item for item in items}

        if self.comparers:
            # match again on current conditions to check for differences from original list
            # which ensures that the paths included in the XML output
            # do not include paths that match any of the comparer or group_by conditions

            # copy the list of tracks as the sorter will modify the list order
            original = original.copy()
            # get the last played track as reference in case comparer is looking for the playing tracks as reference
            ItemSorter.sort_by_field(original, field=Fields.LAST_PLAYED, reverse=True)

            matched_mapped = {
                item.path.casefold(): item for item in self.comparers(original, reference=original[0])
            } if self.comparers.ready else {}
            matched_mapped |= {
                item.path.casefold(): item for item in self._get_group_by_results(original, matched_mapped.values())
            }

            # get new include/exclude paths based on the leftovers after matching on comparers and group_by settings
            self.exclude.values = list(matched_mapped.keys() - items_mapped)
            self.include.values = [v for v in list(items_mapped - matched_mapped.keys()) if v not in self.exclude]
        else:
            matched_mapped = items_mapped

        include_items = tuple(items_mapped[path] for path in self.include if path in items_mapped)
        exclude_items = tuple(matched_mapped[path] for path in self.exclude if path in matched_mapped)

        source = {}
        if len(include_items) > 0:  # assign include paths to XML object
            source["ExceptionsInclude"] = "|".join(path_mapper(include_items)).replace("&", "&amp;")
        if len(exclude_items) > 0:  # assign exclude paths to XML object
            source["Exceptions"] = "|".join(path_mapper(exclude_items)).replace("&", "&amp;")

        return {
            "SmartPlaylist": {
                "@GroupBy": self.group_by.name.lower() if self.group_by else "track",
                "Source": source,
            }
        }

    def __init__(
            self,
            include: U = FilterDefinedList(),
            exclude: V = FilterDefinedList(),
            comparers: X = FilterComparers(),
            group_by: TagField | None = None,
            *_,
            **__
    ):
        super().__init__(comparers, include, exclude)
        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

        #: The filter that, when processed, returns items to include
        self.include = include
        #: The filter that, when processed, returns items to exclude
        self.exclude = exclude
        #: The comparers to use when processing for this filter
        self.comparers = comparers
        #: Once all other filters are applied, also include all other items that match this tag type
        #: from the matched items for the remaining items given
        self.group_by = group_by

    def __call__(self, *args, **kwargs) -> list[T]:
        return self.process(*args, **kwargs)

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

        result = MatchResult(included=included, excluded=excluded, compared=compared)
        grouped = self._get_group_by_results(values, matched=result.combined)

        if not grouped:
            return result
        return MatchResult(included=included, excluded=excluded, compared=compared, grouped=grouped)

    def _get_group_by_results(self, values: Collection[T], matched: Collection[T]) -> tuple[T, ...]:
        if not self.group_by or len(values) == len(matched):
            return ()
        tag_names = self.group_by.to_tag()
        tag_values = {item[tag_name] for item in matched for tag_name in tag_names if hasattr(item, tag_name)}

        return tuple(
            item for item in values
            if item not in matched
            and any(item[tag_name] in tag_values for tag_name in tag_names if hasattr(item, tag_name))
        )

    def as_dict(self):
        return {
            "include": self.include,
            "exclude": self.exclude,
            "comparers": self.comparers,
            "group_by": self.group_by.name.lower() if self.group_by else None
        }
