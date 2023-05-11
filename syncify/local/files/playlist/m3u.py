from dataclasses import dataclass
from datetime import datetime
from os.path import exists, getmtime
from typing import Optional, List, Collection, Union

from syncify.local.files.playlist.playlist import LocalPlaylist
from syncify.local.files.track import LocalTrack, load_track, TrackMatch
from syncify.utils_new.generic import UpdateResult


@dataclass
class UpdateResultM3U(UpdateResult):
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

    valid_extensions = [".m3u"]

    def __init__(
            self,
            path: str,
            tracks: Optional[List[LocalTrack]] = None,
            library_folder: Optional[str] = None,
            other_folders: Optional[Union[str, Collection[str]]] = None,
            check_existence: bool = True
    ):
        self._validate_type(path)

        paths = []
        if exists(path):
            with open(path, "r", encoding='utf-8') as f:
                paths = [line.strip() for line in f]
        elif tracks is not None:
            paths = [track.path for track in tracks]

        matcher = TrackMatch(
            include_paths=paths,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=check_existence
        )
        LocalPlaylist.__init__(self, path=path, matcher=matcher)

        self.load(tracks=tracks)

    def load(self, tracks: Optional[List[LocalTrack]] = None) -> List[LocalTrack]:
        if self.matcher.include_paths is None or len(self.matcher.include_paths) == 0:
            self.tracks = tracks if tracks else []
        elif tracks is not None:
            self._match(tracks)
        else:
            self.tracks = [load_track(path=path) for path in self.matcher.include_paths if path is not None]

        self._limit(ignore=self.matcher.include_paths)
        self._sort()

        if exists(self._path):
            self._tracks_original = self.tracks.copy()
        else:
            self._tracks_original = []

        return self.tracks

    def save(self, dry_run: bool = True) -> UpdateResultM3U:
        start_paths = set(self._prepare_paths_for_output({track.path.lower() for track in self._tracks_original}))

        if not dry_run:
            with open(self.path, "w", encoding='utf-8') as f:
                paths = self._prepare_paths_for_output([track.path for track in self.tracks])
                f.writelines([path.strip() + '\n' for path in paths])
            self.date_modified = datetime.fromtimestamp(getmtime(self._path))

            with open(self.path, "r", encoding='utf-8') as f:
                final_paths = {line.rstrip().lower() for line in f if line.rstrip()}
        else:
            final_paths = {track.path.lower() for track in self._tracks}

        self._tracks_original = self.tracks.copy()
        return UpdateResultM3U(
            start=len(start_paths),
            added=len(final_paths - start_paths),
            removed=len(start_paths - final_paths),
            unchanged=len(start_paths.intersection(final_paths)),
            difference=len(final_paths) - len(start_paths),
            final=len(final_paths),
        )
