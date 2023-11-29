from copy import deepcopy
from dataclasses import dataclass
from os.path import exists
from typing import Any
from collections.abc import Collection, Mapping

import xmltodict

from syncify.abstract.misc import Result
from syncify.enums.tags import PropertyName
from syncify.local.playlist.playlist import LocalPlaylist
from syncify.local.playlist.processor.match import TrackMatch
from syncify.local.playlist.processor.limit import TrackLimit
from syncify.local.playlist.processor.sort import TrackSort
from syncify.local.track import LocalTrack, load_track
from utils import UnitCollection


@dataclass(frozen=True)
class SyncResultXAutoPF(Result):
    """Stores the results of a sync with local a XAutoPF playlist"""
    start: int
    start_description: str
    start_include: int
    start_exclude: int
    start_comparators: int
    start_limiter: bool
    start_sorter: bool

    final: int
    final_description: str
    final_include: int
    final_exclude: int
    final_comparators: int
    final_limiter: bool
    final_sorter: bool


class XAutoPF(LocalPlaylist):
    """
    For reading and writing data from MusicBee's auto-playlist format.

    **Note**: You must provide a list of tracks to search on initialisation for this playlist type.

    :param path: Absolute path of the playlist.
    :param tracks: Available Tracks to search through for matches.
        If none are provided, will load only the paths listed in the ``ExceptionsInclude`` key of the playlist file.
    :param library_folder: Absolute path of folder containing tracks.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param check_existence: If True, when processing paths,
        check for the existence of the file paths on the file system and reject any that don't.
    """

    valid_extensions = {".xautopf"}

    @property
    def image_links(self):
        return {}

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value: str | None):
        self._description = value

    def __init__(
            self,
            path: str,
            tracks: Collection[LocalTrack] | None = None,
            library_folder: str | None = None,
            other_folders: UnitCollection[str] | None = None,
            check_existence: bool = True
    ):
        self._validate_type(path)
        if not exists(path):
            # TODO: implement creation of auto-playlist from scratch (very low priority)
            raise NotImplementedError(
                f"No playlist at given path: {path}. "
                "This program is not yet able to create this playlist type from scratch."
            )

        with open(path, "r", encoding="utf-8") as f:
            self.xml: dict[str, Any] = xmltodict.parse(f.read())

        self._description = self.xml["SmartPlaylist"]["Source"]["Description"]

        # generate track processors from the XML settings
        matcher = TrackMatch.from_xml(xml=self.xml)
        matcher.library_folder = library_folder
        matcher.sanitise_file_paths(other_folders, check_existence=check_existence)
        limiter = TrackLimit.from_xml(xml=self.xml)
        sorter = TrackSort.from_xml(xml=self.xml)

        LocalPlaylist.__init__(self, path=path, matcher=matcher, limiter=limiter, sorter=sorter)

        self._tracks_original: list[LocalTrack]
        self.load(tracks=tracks)

    def load(self, tracks: Collection[LocalTrack] | None = None) -> list[LocalTrack] | None:
        if tracks is None:
            tracks = [load_track(path=path) for path in self.matcher.include_paths if path is not None]

        self.sorter.sort_by_field(tracks, field=PropertyName.LAST_PLAYED, reverse=True)
        self._match(tracks=tracks, reference=tracks[0] if len(tracks) > 0 else None)
        self._limit(ignore=self.matcher.include_paths)
        self._sort()

        self._tracks_original = self.tracks.copy()
        return tracks

    def save(self, dry_run: bool = True) -> SyncResultXAutoPF:
        start_xml = deepcopy(self.xml)

        # update the stored XML object
        self.xml["SmartPlaylist"]["Source"]["Description"] = self.description
        self._update_xml_paths()
        # self._update_comparators()
        # self._update_limiter()
        # self._update_sorter()

        if not dry_run:  # save the modified XML object to file
            self._save_xml()

        # generate stats for logging
        count_start = len(self._tracks_original)
        self._tracks_original = self.tracks.copy()
        start_source: Mapping[str, Any] = start_xml["SmartPlaylist"]["Source"]
        final_source: Mapping[str, Any] = self.xml["SmartPlaylist"]["Source"]

        return SyncResultXAutoPF(
            start=count_start,
            start_description=start_source["Description"],
            start_include=len([p for p in start_source.get("ExceptionsInclude", "").split("|") if p]),
            start_exclude=len([p for p in start_source.get("Exceptions", "").split("|") if p]),
            start_comparators=len(start_source["Conditions"].get("Condition", [])),
            start_limiter=start_source["Limit"].get("@Enabled", "False") == "True",
            start_sorter=len(start_source.get("SortBy", start_source.get("DefinedSort", []))) > 0,
            final=len(self._tracks_original),
            final_description=final_source["Description"],
            final_include=len([p for p in final_source.get("ExceptionsInclude", "").split("|") if p]),
            final_exclude=len([p for p in final_source.get("Exceptions", "").split("|") if p]),
            final_comparators=len(final_source["Conditions"].get("Condition", [])),
            final_limiter=final_source["Limit"].get("@Enabled", "False") == "True",
            final_sorter=len(final_source.get("SortBy", final_source.get("DefinedSort", []))) > 0,
        )

    # noinspection PyTypeChecker
    def _update_xml_paths(self) -> None:
        tracks = self._tracks_original

        path_track_map: Mapping[str: LocalTrack] = {track.path.lower(): track for track in self.tracks}

        # match again on current conditions to check differences
        self.sorter.sort_by_field(tracks, field=PropertyName.LAST_PLAYED, reverse=True)
        matches: list[LocalTrack] = self.matcher.match(tracks, reference=tracks[0], combine=False).compared
        compared: Mapping[str: LocalTrack] = {track.path.lower(): track for track in matches}

        # get new include/exclude paths based on the leftovers after matching on comparators
        self.matcher.include_paths = list(path_track_map - compared.keys())
        self.matcher.exclude_paths = list(compared.keys() - path_track_map)

        # get the track objects related to these paths and their actual paths as stored in their objects
        include_tracks: tuple[LocalTrack | None] = tuple(path_track_map.get(p) for p in self.matcher.include_paths)
        exclude_tracks: tuple[LocalTrack | None] = tuple(compared.get(p) for p in self.matcher.exclude_paths)
        include_paths: tuple[str] = tuple(track.path for track in include_tracks if track is not None)
        exclude_paths: tuple[str] = tuple(track.path for track in exclude_tracks if track is not None)

        source = self.xml["SmartPlaylist"]["Source"]

        if len(include_paths) > 0:  # assign include paths to XML object
            source["ExceptionsInclude"] = "|".join(self._prepare_paths_for_output(include_paths))
        else:
            source.pop("ExceptionsInclude", None)

        if len(exclude_paths) > 0:  # assign exclude paths to XML object
            source["Exceptions"] = "|".join(self._prepare_paths_for_output(exclude_paths))
        else:
            source.pop("Exceptions", None)

    def _update_comparators(self) -> None:
        # TODO: implement comparison XML part updater (low priority)
        raise NotImplementedError

    def _update_limiter(self) -> None:
        # TODO: implement limit XML part updater (low priority)
        raise NotImplementedError

    def _update_sorter(self) -> None:
        # TODO: implement sort XML part updater (low priority)
        raise NotImplementedError

    def _save_xml(self) -> None:
        """Save XML representation of the playlist"""
        with open(self.path, 'w', encoding="utf-8") as f:
            xml_str = xmltodict.unparse(self.xml, pretty=True, short_empty_elements=True)
            f.write(xml_str.replace("/>", " />").replace('\t', '  '))
