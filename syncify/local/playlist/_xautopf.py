from collections.abc import Collection, Mapping, Iterable
from copy import deepcopy
from dataclasses import dataclass
from os.path import exists
from typing import Any

import xmltodict

from syncify.abstract.enums import FieldCombined
from syncify.abstract.misc import Result
from syncify.local.playlist._match import LocalMatcher
from syncify.local.playlist._playlist import LocalPlaylist
from syncify.local.track import LocalTrack
from syncify.processors.limit import ItemLimiter
from syncify.processors.sort import ItemSorter
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitCollection


@dataclass(frozen=True)
class SyncResultXAutoPF(Result):
    """
    Stores the results of a sync with a local XAutoPF playlist

    :ivar start: The total number of tracks in the playlist before the sync.
    :ivar start_description: The description of the playlist before sync.
    :ivar start_include: The number of tracks that matched the include settings before the sync.
    :ivar start_exclude: The number of tracks that matched the exclude settings before the sync.
    :ivar start_comparers: The number of tracks that matched all the :py:class:`ItemComparer` settings before the sync.
    :ivar start_limiter: Was a limiter present on the playlist before the sync.
    :ivar start_sorter: Was a sorter present on the playlist before the sync.

    :ivar final: The total number of tracks in the playlist after the sync.
    :ivar final_description: The description of the playlist after sync.
    :ivar final_include: The number of tracks that matched the include settings after the sync.
    :ivar final_exclude: The number of tracks that matched the exclude settings after the sync.
    :ivar final_comparers: The number of tracks that matched all the :py:class:`ItemComparer` settings after the sync.
    :ivar final_limiter: Was a limiter present on the playlist after the sync.
    :ivar final_sorter: Was a sorter present on the playlist after the sync.
    """
    start: int
    start_description: str
    start_include: int
    start_exclude: int
    start_comparers: int
    start_limiter: bool
    start_sorter: bool

    final: int
    final_description: str
    final_include: int
    final_exclude: int
    final_comparers: int
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
    :param available_track_paths: A list of available track paths that are known to exist
        and are valid for the track types supported by this program.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
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

    def __init__(
            self,
            path: str,
            tracks: Collection[LocalTrack] = (),
            library_folder: str | None = None,
            other_folders: UnitCollection[str] = (),
            check_existence: bool = True,
            available_track_paths: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
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

        matcher = LocalMatcher.from_xml(
            xml=self.xml, library_folder=library_folder, other_folders=other_folders, check_existence=check_existence
        )
        super().__init__(
            path=path,
            matcher=matcher,
            limiter=ItemLimiter.from_xml(xml=self.xml),
            sorter=ItemSorter.from_xml(xml=self.xml),
            available_track_paths=available_track_paths,
            remote_wrangler=remote_wrangler,
        )

        self._tracks_original: list[LocalTrack]
        self.load(tracks=tracks)

    def load(self, tracks: Collection[LocalTrack] | None = None) -> list[LocalTrack] | None:
        if tracks is None:
            tracks = [self._load_track(path) for path in self.matcher.include_paths if path is not None]

        self.sorter.sort_by_field(tracks, field=FieldCombined.LAST_PLAYED, reverse=True)
        self._match(tracks=tracks, reference=tracks[0] if len(tracks) > 0 else None)
        self._limit(ignore=self.matcher.include_paths)
        self._sort()

        self._tracks_original = self.tracks.copy()
        return tracks

    def save(self, dry_run: bool = True, *_, **__) -> SyncResultXAutoPF:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: The results of the sync as a :py:class:`SyncResultXAutoPF` object.
        """
        start_xml = deepcopy(self.xml)

        # update the stored XML object
        self.xml["SmartPlaylist"]["Source"]["Description"] = self.description
        self._update_xml_paths()
        # self._update_comparers()
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
            start_comparers=len(start_source["Conditions"].get("Condition", [])),
            start_limiter=start_source["Limit"].get("@Enabled", "False") == "True",
            start_sorter=len(start_source.get("SortBy", start_source.get("DefinedSort", []))) > 0,
            final=len(self._tracks_original),
            final_description=final_source["Description"],
            final_include=len([p for p in final_source.get("ExceptionsInclude", "").split("|") if p]),
            final_exclude=len([p for p in final_source.get("Exceptions", "").split("|") if p]),
            final_comparers=len(final_source["Conditions"].get("Condition", [])),
            final_limiter=final_source["Limit"].get("@Enabled", "False") == "True",
            final_sorter=len(final_source.get("SortBy", final_source.get("DefinedSort", []))) > 0,
        )

    def _update_xml_paths(self) -> None:
        """Update the stored, parsed XML object with valid include and exclude paths"""
        source = self.xml["SmartPlaylist"]["Source"]
        output = self.matcher.to_xml(
            tracks=self.tracks, tracks_original=self._tracks_original, path_mapper=self._prepare_paths_for_output
        )

        # assign values to stored, parsed XML map
        for k, v in output.items():
            source.pop(k, None)
            if output.get(k):
                source[k] = v

    def _update_comparers(self) -> None:
        """Update the stored, parsed XML object with appropriately formatted comparer settings"""
        # TODO: implement comparison XML part updater (low priority)
        raise NotImplementedError

    def _update_limiter(self) -> None:
        """Update the stored, parsed XML object with appropriately formatted limiter settings"""
        # TODO: implement limit XML part updater (low priority)
        raise NotImplementedError

    def _update_sorter(self) -> None:
        """Update the stored, parsed XML object with appropriately formatted sorter settings"""
        # TODO: implement sort XML part updater (low priority)
        raise NotImplementedError

    def _save_xml(self) -> None:
        """Save XML representation of the playlist"""
        with open(self.path, 'w', encoding="utf-8") as f:
            xml_str = xmltodict.unparse(self.xml, pretty=True, short_empty_elements=True)
            f.write(xml_str.replace("/>", " />").replace('\t', '  '))
