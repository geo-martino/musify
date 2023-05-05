from copy import deepcopy
from dataclasses import dataclass
from os.path import exists
from typing import Any, List, Mapping, Optional, Set

import xmltodict

from syncify.local.files.playlist import Playlist, UpdateResult
from syncify.local.files.track import PropertyName, Track, TrackMatch, TrackLimit, TrackSort


@dataclass
class UpdateResultXAutoPF(UpdateResult):
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


class XAutoPF(Playlist):
    """
    For reading and writing data from MusicBee's auto-playlist format.

    **Note**: You must provide a list of tracks to search on initialisation for this playlist type.

    :param path: Full path of the playlist.
    :param tracks: **Required**. Available Tracks to search through for matches.
    :param library_folder: Full path of folder containing tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    valid_extensions = [".xautopf"]

    def __init__(
            self,
            path: str,
            tracks: List[Track],
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None
    ):
        self._validate_type(path)

        if not exists(path):
            raise NotImplementedError(
                f"No playlist at given path: {path}. "
                "This program is not yet able to create this playlist type from scratch."
            )

        with open(path, "r", encoding='utf-8') as f:
            self.xml: Mapping[str, Any] = xmltodict.parse(f.read())

        Playlist.__init__(
            self,
            path=path,
            library_folder=library_folder,
            other_folders=other_folders,
            matcher=TrackMatch.from_xml(xml=self.xml),
            limiter=TrackLimit.from_xml(xml=self.xml),
            sorter=TrackSort.from_xml(xml=self.xml)
        )
        self.description = self.xml["SmartPlaylist"]["Source"]["Description"]

        self.load(tracks=tracks)
        self._count_last_save = len(self.tracks)

    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        """
        Read the playlist file.

        **Note**: You must provide a list of tracks for this playlist type.

        :param tracks: **Required**. Available Tracks to search through for matches.
        :return: Ordered list of tracks in this playlist
        """
        if tracks is None:
            raise ValueError("This playlist type requires that you provide a list of loaded tracks")

        self.sorter.sort_by_field(tracks, field=PropertyName.LAST_PLAYED, reverse=True)
        self._match(tracks, reference=tracks[0])
        self._limit(ignore=self.matcher.include_paths)
        self._sort()

        return tracks

    def write(self) -> UpdateResultXAutoPF:
        start_xml = deepcopy(self.xml)

        self._update_xml_paths()
        # self._update_comparators()
        # self._update_limiter()
        # self._update_sorter()

        self._save_xml()

        count_start = self._count_last_save
        self._count_last_save = len(self.tracks)

        start_source: Mapping[str, Any] = start_xml["SmartPlaylist"]["Source"]
        final_source: Mapping[str, Any] = self.xml["SmartPlaylist"]["Source"]

        return UpdateResultXAutoPF(
            start=count_start,
            start_description=start_source["Description"],
            start_include=len([p for p in start_source.get("ExceptionsInclude", "").split("|") if p]),
            start_exclude=len([p for p in start_source.get("Exceptions", "").split("|") if p]),
            start_comparators=len(start_source.get("Conditions", [])),
            start_limiter=len(start_source.get("Limit", [])) > 0,
            start_sorter=len(start_source.get("SortBy", start_source.get("DefinedSort", []))) > 0,
            final=self._count_last_save,
            final_description=final_source["Description"],
            final_include=len([p for p in final_source.get("ExceptionsInclude", "").split("|") if p]),
            final_exclude=len([p for p in final_source.get("Exceptions", "").split("|") if p]),
            final_comparators=len(final_source.get("Conditions", [])),
            final_limiter=len(final_source.get("Limit", [])) > 0,
            final_sorter=len(final_source.get("SortBy", final_source.get("DefinedSort", []))) > 0,
        )

    # noinspection PyTypeChecker
    def _update_xml_paths(self) -> None:
        tracks = self.tracks.copy()
        path_track_map: Mapping[str: Track] = {track.path.lower(): track for track in tracks}

        # match again on current conditions to check differences
        self.sorter.sort_by_field(tracks, field=PropertyName.LAST_PLAYED, reverse=True)
        matches: List[Track] = self.matcher.match(tracks, reference=tracks[0], combine=False)[2]
        compared: Mapping[str: Track] = {track.path.lower(): track for track in matches}

        self.matcher.include_paths = list(path_track_map - compared.keys())
        self.matcher.exclude_paths = list(compared.keys() - path_track_map)

        include_tracks: List[Optional[Track]] = [path_track_map.get(path) for path in self.matcher.include_paths]
        exclude_tracks: List[Optional[Track]] = [compared.get(path) for path in self.matcher.exclude_paths]

        include_paths: List[str] = [track.path for track in include_tracks if track is not None]
        exclude_paths: List[str] = [track.path for track in exclude_tracks if track is not None]

        source = self.xml["SmartPlaylist"]["Source"]

        if len(include_paths) > 0:
            source["ExceptionsInclude"] = "|".join(self._prepare_paths_for_output(include_paths))
        else:
            source.pop("ExceptionsInclude", None)

        if len(exclude_paths) > 0:
            source["Exceptions"] = "|".join(self._prepare_paths_for_output(exclude_paths))
        else:
            source.pop("Exceptions", None)

    def _update_comparators(self) -> None:
        raise NotImplementedError

    def _update_limiter(self) -> None:
        raise NotImplementedError

    def _update_sorter(self) -> None:
        raise NotImplementedError

    def _save_xml(self) -> None:
        """Save XML representation of the playlist"""
        with open(self.path, 'w', encoding='utf-8') as f:
            xml_str = xmltodict.unparse(self.xml, pretty=True, short_empty_elements=True)
            f.write(xml_str.replace('/>', ' />').replace('\t', '  '))
