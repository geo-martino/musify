import os
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from os.path import exists, dirname

from syncify.abstract.misc import Result
from syncify.local.playlist.match import LocalMatcher
from syncify.local.playlist.playlist import LocalPlaylist
from syncify.local.track import LocalTrack
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitCollection


@dataclass(frozen=True)
class SyncResultM3U(Result):
    """
    Stores the results of a sync with a local M3U playlist

    :ivar start: The total number of tracks in the playlist before the sync.
    :ivar added: The number of tracks added to the playlist.
    :ivar removed: The number of tracks removed from the playlist.
    :ivar unchanged: The number of tracks that were in the playlist before and after the sync.
    :ivar difference: The difference between the total number tracks in the playlist from before and after the sync.
    :ivar final: The total number of tracks in the playlist after the sync.
    """
    start: int
    added: int
    removed: int
    unchanged: int
    difference: int
    final: int


class M3U(LocalPlaylist):
    """
    For reading and writing data from M3U playlist format.
    You must provide either a valid playlist path of a file that exists,
    or a list of tracks to use as this playlist's tracks.
    You may also provide both to use and store the loaded tracks to this instance.

    :param path: Absolute path of the playlist.
        If the playlist ``path`` given does not exist, the playlist instance will use all the tracks
        given in ``tracks`` as the tracks in the playlist.
    :param tracks: Optional. Available Tracks to search through for matches.
        If no tracks are given, the playlist instance load all the tracks from paths
        listed in file at the playlist ``path``.
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

    valid_extensions = frozenset({".m3u"})

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
            tracks: Collection[LocalTrack] = (),
            library_folder: str | None = None,
            other_folders: UnitCollection[str] = (),
            check_existence: bool = True,
            available_track_paths: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        self._validate_type(path)

        if exists(path):  # load from file
            with open(path, "r", encoding="utf-8") as f:
                paths = [line.strip() for line in f]
        else:  # generating a new M3U
            paths = [track.path for track in tracks]

        self._description = None

        matcher = LocalMatcher(
            include_paths=paths,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=check_existence,
        )
        super().__init__(
            path=path, matcher=matcher, available_track_paths=available_track_paths, remote_wrangler=remote_wrangler,
        )

        self.load(tracks=tracks)

    def load(self, tracks: Collection[LocalTrack] = ()) -> list[LocalTrack]:
        if not self.matcher.include_paths:
            # use the given tracks if no valid matcher present
            self.tracks = tracks if tracks else []
        elif tracks:  # match paths from given tracks using the matcher
            self._match(tracks)
        else:  # use the paths in the matcher to load tracks from scratch
            self.tracks = [self._load_track(path) for path in self.matcher.include_paths if path is not None]

        self._limit(ignore=self.matcher.include_paths)
        self._sort()

        self._tracks_original = self.tracks.copy() if exists(self._path) else []
        return self.tracks

    def save(self, dry_run: bool = True, *_, **__) -> SyncResultM3U:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: The results of the sync as a :py:class:`SyncResultM3U` object.
        """
        start_paths = set(self._prepare_paths_for_output({track.path.casefold() for track in self._tracks_original}))
        os.makedirs(dirname(self.path), exist_ok=True)

        if not dry_run:
            with open(self.path, "w", encoding="utf-8") as f:
                # reassign any original folder found by the matcher and output
                paths = self._prepare_paths_for_output(tuple(track.path for track in self.tracks))
                f.writelines(path.strip() + '\n' for path in paths)

            with open(self.path, "r", encoding="utf-8") as f:  # get list of paths that were saved for logging
                final_paths = {line.rstrip().casefold() for line in f if line.rstrip()}
        else:  # use current list of tracks as a proxy of paths that were saved for logging
            final_paths = {track.path.casefold() for track in self._tracks}

        self._tracks_original = self.tracks.copy()
        return SyncResultM3U(
            start=len(start_paths),
            added=len(final_paths - start_paths),
            removed=len(start_paths - final_paths),
            unchanged=len(start_paths.intersection(final_paths)),
            difference=len(final_paths) - len(start_paths),
            final=len(final_paths),
        )
