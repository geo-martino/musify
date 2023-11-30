from collections.abc import Collection, Iterable
from dataclasses import dataclass
from os.path import exists

from syncify.abstract.misc import Result
from syncify.local.track import LocalTrack
from syncify.utils import UnitCollection
from .playlist import LocalPlaylist
from .processor.match import TrackMatcher


@dataclass(frozen=True)
class SyncResultM3U(Result):
    """Stores the results of a sync with a local M3U playlist"""
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
            tracks: Collection[LocalTrack] | None = None,
            library_folder: str | None = None,
            other_folders: UnitCollection[str] | None = None,
            check_existence: bool = True,
            available_track_paths: Iterable[str] | None = None,
    ):
        self._validate_type(path)

        paths = []
        if exists(path):  # load from file
            with open(path, "r", encoding="utf-8") as f:
                paths = [line.strip() for line in f]
        elif tracks is not None:  # generating a new M3U
            paths = [track.path for track in tracks]

        self._description = None

        matcher = TrackMatcher(
            include_paths=paths,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=check_existence
        )
        LocalPlaylist.__init__(self, path=path, matcher=matcher, available_track_paths=available_track_paths)

        self.load(tracks=tracks)

    def load(self, tracks: Collection[LocalTrack] | None = None) -> list[LocalTrack]:

        if self.matcher.include_paths is None or len(self.matcher.include_paths) == 0:
            # use the given tracks if no valid matcher present
            self.tracks = tracks if tracks else []
        elif tracks is not None:  # match paths from given tracks using the matcher
            self._match(tracks)
        else:  # use the paths in the matcher to load tracks from scratch
            self.tracks = [self._load_track(path) for path in self.matcher.include_paths if path is not None]

        self._limit(ignore=self.matcher.include_paths)
        self._sort()

        self._tracks_original = self.tracks.copy() if exists(self._path) else []
        return self.tracks

    def save(self, dry_run: bool = True) -> SyncResultM3U:
        start_paths = set(self._prepare_paths_for_output({track.path.lower() for track in self._tracks_original}))

        if not dry_run:
            with open(self.path, "w", encoding="utf-8") as f:
                # reassign any original folder found by the matcher and output
                paths = self._prepare_paths_for_output(tuple(track.path for track in self.tracks))
                f.writelines(path.strip() + '\n' for path in paths)

            with open(self.path, "r", encoding="utf-8") as f:  # get list of paths that were saved for logging
                final_paths = {line.rstrip().lower() for line in f if line.rstrip()}
        else:  # use current list of tracks as a proxy of paths that were saved for logging
            final_paths = {track.path.lower() for track in self._tracks}

        self._tracks_original = self.tracks.copy()
        return SyncResultM3U(
            start=len(start_paths),
            added=len(final_paths - start_paths),
            removed=len(start_paths - final_paths),
            unchanged=len(start_paths.intersection(final_paths)),
            difference=len(final_paths) - len(start_paths),
            final=len(final_paths),
        )
