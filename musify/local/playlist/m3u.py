"""
The M3U implementation of a :py:class:`LocalPlaylist`.
"""

import os
from collections.abc import Collection
from dataclasses import dataclass
from os.path import exists, dirname

from musify.local.file import PathMapper, File
from musify.local.playlist.base import LocalPlaylist
from musify.local.track import LocalTrack, load_track
from musify.processors.filter import FilterDefinedList
from musify.shared.core.misc import Result
from musify.shared.remote.processors.wrangle import RemoteDataWrangler


@dataclass(frozen=True)
class SyncResultM3U(Result):
    """Stores the results of a sync with a local M3U playlist"""
    #: The total number of tracks in the playlist before the sync.
    start: int
    #: The number of tracks added to the playlist.
    added: int
    #: The number of tracks removed from the playlist.
    removed: int
    #: The number of tracks that were in the playlist before and after the sync.
    unchanged: int
    #: The difference between the total number tracks in the playlist from before and after the sync.
    difference: int
    #: The total number of tracks in the playlist after the sync.
    final: int


class M3U(LocalPlaylist[FilterDefinedList[str | File]]):
    """
    For reading and writing data from M3U playlist format.
    You must provide either a valid playlist path of a file that exists,
    or a list of tracks to use as this playlist's tracks.
    You may also provide both to use and store the loaded tracks to this instance.

    :param path: Absolute path of the playlist.
        If the playlist ``path`` given does not exist, the playlist instance will use all the tracks
        given in ``tracks`` as the tracks in the playlist.
    :param tracks: Optional. Available Tracks to search through for matches.
        If no tracks are given, the playlist instance will load all the tracks from scratch according to its settings.
    :param path_mapper: Optionally, provide a :py:class:`PathMapper` for paths stored in the playlist file.
        Useful if the playlist file contains relative paths and/or paths for other systems that need to be
        mapped to absolute, system-specific paths to be loaded and back again when saved.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    __slots__ = ("_description",)

    valid_extensions = frozenset({".m3u"})

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
            path_mapper: PathMapper = PathMapper(),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        self._validate_type(path)

        if exists(path):  # load from file
            with open(path, "r", encoding="utf-8") as file:
                paths = path_mapper.map_many([line.strip() for line in file], check_existence=True)
        else:  # generating a new M3U
            paths = [track.path for track in tracks]

        self._description = None
        super().__init__(
            path=path,
            matcher=FilterDefinedList(values=[path.casefold() for path in paths]),
            path_mapper=path_mapper,
            remote_wrangler=remote_wrangler
        )
        self.matcher.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()

        self.load(tracks=tracks)

    def _load_track(self, path: str) -> LocalTrack:
        return load_track(path=self.path_mapper.map(path, check_existence=True), remote_wrangler=self.remote_wrangler)

    def load(self, tracks: Collection[LocalTrack] = ()) -> list[LocalTrack]:
        if tracks:  # match paths from given tracks using the matcher
            self._match(tracks)
        else:  # use the paths in the matcher to load tracks from scratch
            self.tracks = [self._load_track(path) for path in self.matcher.values if path is not None]

        self._limit(ignore=self.matcher.values)
        self._sort()

        self._original = self.tracks.copy() if exists(self._path) else []
        return self.tracks

    def save(self, dry_run: bool = True, *_, **__) -> SyncResultM3U:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: The results of the sync as a :py:class:`SyncResultM3U` object.
        """
        start_paths = {path.casefold() for path in self.path_mapper.unmap_many(self._original, check_existence=False)}
        os.makedirs(dirname(self.path), exist_ok=True)

        if not dry_run:
            with open(self.path, "w", encoding="utf-8") as file:
                # reassign any original folder found by the matcher and output
                paths = self.path_mapper.unmap_many(self.tracks, check_existence=False)
                file.writelines(path.strip() + '\n' for path in paths)

            self._original = self.tracks.copy()  # update original tracks to newly saved tracks

            with open(self.path, "r", encoding="utf-8") as file:  # get list of paths that were saved for results
                final_paths = {line.rstrip().casefold() for line in file if line.rstrip()}
        else:  # use current list of tracks as a proxy of paths that were saved for results
            final_paths = {track.path.casefold() for track in self._tracks}

        return SyncResultM3U(
            start=len(start_paths),
            added=len(final_paths - start_paths),
            removed=len(start_paths - final_paths),
            unchanged=len(start_paths.intersection(final_paths)),
            difference=len(final_paths) - len(start_paths),
            final=len(final_paths),
        )
