"""
The XAutoPF implementation of a :py:class:`LocalPlaylist`.
"""

from collections.abc import Collection
from copy import deepcopy
from dataclasses import dataclass
from os.path import exists
from typing import Any

import xmltodict

from musify.local.file import PathMapper
from musify.local.playlist.base import LocalPlaylist
from musify.local.track import LocalTrack
from musify.processors.filter import FilterDefinedList, FilterComparers
from musify.processors.filter_matcher import FilterMatcher
from musify.processors.limit import ItemLimiter
from musify.processors.sort import ItemSorter
from musify.shared.core.enum import Fields
from musify.shared.core.misc import Result


@dataclass(frozen=True)
class SyncResultXAutoPF(Result):
    """Stores the results of a sync with a local XAutoPF playlist."""
    #: The total number of tracks in the playlist before the sync.
    start: int
    #: The description of the playlist before sync.
    start_description: str
    #: The number of tracks that matched the include settings before the sync.
    start_included: int
    #: The number of tracks that matched the exclude settings before the sync.
    start_excluded: int
    #: The number of tracks that matched all the :py:class:`Comparer` settings before the sync.
    start_compared: int
    #: Was a limiter present on the playlist before the sync.
    start_limiter: bool
    #: Was a sorter present on the playlist before the sync.
    start_sorter: bool

    #: The total number of tracks in the playlist after the sync.
    final: int
    #: The description of the playlist after sync.
    final_description: str
    #: The number of tracks that matched the include settings after the sync.
    final_included: int
    #: The number of tracks that matched the exclude settings after the sync.
    final_excluded: int
    #: The number of tracks that matched all the :py:class:`Comparer` settings after the sync.
    final_compared: int
    #: Was a limiter present on the playlist after the sync.
    final_limiter: bool
    #: Was a sorter present on the playlist after the sync.
    final_sorter: bool


class XAutoPF(LocalPlaylist[FilterMatcher[
    LocalTrack, FilterDefinedList[LocalTrack], FilterDefinedList[LocalTrack], FilterComparers[LocalTrack]
]]):
    """
    For reading and writing data from MusicBee's auto-playlist format.

    **Note**: You must provide a list of tracks to search on initialisation for this playlist type.

    :param path: Absolute path of the playlist.
    :param tracks: Optional. Available Tracks to search through for matches.
        If none are provided, no tracks will be loaded initially
    :param path_mapper: Optionally, provide a :py:class:`PathMapper` for paths stored in the playlist file.
        Useful if the playlist file contains relative paths and/or paths for other systems that need to be
        mapped to absolute, system-specific paths to be loaded and back again when saved.
    """

    __slots__ = ("_description", "xml",)

    valid_extensions = frozenset({".xautopf"})

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value: str | None):
        self._description = value

    @property
    def image_links(self):
        return {}

    def __init__(self, path: str, tracks: Collection[LocalTrack] = (), path_mapper: PathMapper = PathMapper()):
        self._validate_type(path)
        if not exists(path):
            # TODO: implement creation of auto-playlist from scratch (very low priority)
            raise NotImplementedError(
                f"No playlist at given path: {path}. "
                "This program is not yet able to create this playlist type from scratch."
            )

        with open(path, "r", encoding="utf-8") as file:
            #: A map representation of the loaded XML playlist data
            self.xml: dict[str, Any] = xmltodict.parse(file.read())

        self._description = self.xml["SmartPlaylist"]["Source"]["Description"]

        super().__init__(
            path=path,
            matcher=FilterMatcher.from_xml(xml=self.xml, path_mapper=path_mapper),
            limiter=ItemLimiter.from_xml(xml=self.xml),
            sorter=ItemSorter.from_xml(xml=self.xml),
            path_mapper=path_mapper,
        )

        self.load(tracks=tracks)

    def load(self, tracks: Collection[LocalTrack] = ()) -> list[LocalTrack]:
        tracks_list = list(tracks)
        self.sorter.sort_by_field(tracks_list, field=Fields.LAST_PLAYED, reverse=True)

        self._match(tracks=tracks, reference=tracks_list[0] if len(tracks) > 0 else None)
        self._limit(ignore=self.matcher.exclude)
        self._sort()

        self._original = self.tracks.copy()
        return self.tracks

    def save(self, dry_run: bool = True, *_, **__) -> SyncResultXAutoPF:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: The results of the sync as a :py:class:`SyncResultXAutoPF` object.
        """
        xml_start = deepcopy(self.xml)
        xml_final = deepcopy(self.xml)

        count_start = len(self._original)
        source_start: dict[str, Any] = xml_start["SmartPlaylist"]["Source"]
        source_final: dict[str, Any] = xml_final["SmartPlaylist"]["Source"]

        # update the stored XML object
        source_final["Description"] = self.description
        self._update_xml_paths(xml_final)
        # self._update_comparers(xml_final)
        # self._update_limiter(xml_final)
        # self._update_sorter(xml_final)

        if not dry_run:  # save the modified XML object to file and update stored values
            self.xml = xml_final
            self._save_xml()
            self._original = self.tracks.copy()

        return SyncResultXAutoPF(
            start=count_start,
            start_description=source_start["Description"],
            start_included=len([p for p in source_start.get("ExceptionsInclude", "").split("|") if p]),
            start_excluded=len([p for p in source_start.get("Exceptions", "").split("|") if p]),
            start_compared=len(source_start["Conditions"].get("Condition", [])),
            start_limiter=source_start["Limit"].get("@Enabled", "False") == "True",
            start_sorter=len(source_start.get("SortBy", source_start.get("DefinedSort", []))) > 0,
            final=len(self.tracks),
            final_description=source_final["Description"],
            final_included=len([p for p in source_final.get("ExceptionsInclude", "").split("|") if p]),
            final_excluded=len([p for p in source_final.get("Exceptions", "").split("|") if p]),
            final_compared=len(source_final["Conditions"].get("Condition", [])),
            final_limiter=source_final["Limit"].get("@Enabled", "False") == "True",
            final_sorter=len(source_final.get("SortBy", source_final.get("DefinedSort", []))) > 0,
        )

    def _update_xml_paths(self, xml: dict[str, Any]) -> None:
        """Update the stored, parsed XML object with valid include and exclude paths"""
        source = xml["SmartPlaylist"]["Source"]
        output = self.matcher.to_xml(
            items=self.tracks,
            original=self._original,
            path_mapper=lambda paths: self.path_mapper.unmap_many(paths, check_existence=False)
        )

        # assign values to stored, parsed XML map
        for k, v in output.items():
            source.pop(k, None)
            if output.get(k):
                source[k] = v

    def _update_comparers(self, xml: dict[str, Any]) -> None:
        """Update the stored, parsed XML object with appropriately formatted comparer settings"""
        # TODO: implement comparison XML part updater (low priority)
        raise NotImplementedError

    def _update_limiter(self, xml: dict[str, Any]) -> None:
        """Update the stored, parsed XML object with appropriately formatted limiter settings"""
        # TODO: implement limit XML part updater (low priority)
        raise NotImplementedError

    def _update_sorter(self, xml: dict[str, Any]) -> None:
        """Update the stored, parsed XML object with appropriately formatted sorter settings"""
        # TODO: implement sort XML part updater (low priority)
        raise NotImplementedError

    def _save_xml(self) -> None:
        """Save XML representation of the playlist"""
        with open(self.path, 'w', encoding="utf-8") as file:
            xml_str = xmltodict.unparse(self.xml, pretty=True, short_empty_elements=True)
            file.write(xml_str.replace("/>", " />").replace('\t', '  '))
