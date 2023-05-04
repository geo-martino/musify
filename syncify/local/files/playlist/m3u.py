from dataclasses import dataclass
from typing import Optional, List, Set

from syncify.local.files import TrackMatch
from syncify.local.files.playlist import Playlist, UpdateResult
from syncify.local.files.track import Track, load_track


@dataclass
class UpdateResultM3U(UpdateResult):
    start: int
    added: int
    removed: int
    unchanged: int
    difference: int
    final: int


class M3U(Playlist):
    """
    For reading and writing data from M3U playlist format.

    :param path: Full path of the playlist.
    :param tracks: Available Tracks to search through for matches. Optional.
    :param library_folder: Full path of folder containing tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    playlist_ext = [".m3u"]

    def __init__(
            self,
            path: Optional[str],
            tracks: List[Track],
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None
    ):
        with open(path, "r", encoding='utf-8') as f:
            matcher = TrackMatch(
                include_paths=[line.strip() for line in f], library_folder=library_folder, other_folders=other_folders
            )

        Playlist.__init__(
            self,
            path=path,
            tracks=tracks,
            library_folder=library_folder,
            other_folders=other_folders,
            matcher=matcher
        )

        self.matcher.sanitise_file_paths(library_folder=library_folder, other_folders=other_folders)

        self.load(tracks=tracks)

    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        if self.matcher.include_paths is None or len(self.matcher.include_paths) == 0:
            return

        if tracks is None:
            self.tracks = [load_track(path=path) for path in self.matcher.include_paths if path is not None]
        else:
            self._match(tracks)

        return self.tracks

    def write(self) -> UpdateResultM3U:
        with open(self.path, "r", encoding='utf-8') as f:
            start_paths = {line.rstrip().lower() for line in f}
            start_paths = {path for path in start_paths if path}

        with open(self.path, "w", encoding='utf-8') as f:
            paths = self._prepare_paths_for_output([track.path for track in self.tracks])
            f.writelines([path.strip() + '\n' for path in paths])

        with open(self.path, "r", encoding='utf-8') as f:
            final_paths = {line.rstrip().lower() for line in f}
            final_paths = {path for path in final_paths if path}

        return UpdateResultM3U(
            start=len(start_paths),
            added=len(final_paths - start_paths),
            removed=len(start_paths - final_paths),
            unchanged=len(start_paths.intersection(final_paths)),
            difference=len(final_paths) - len(start_paths),
            final=len(final_paths),
        )
