from typing import Optional, List, Set

from syncify.local.files.file import load_track
from syncify.local.files.track.track import Track
from syncify.local.files.playlist.playlist import Playlist


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
            path: str,
            tracks: List[Track],
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None
    ):
        Playlist.__init__(self, path=path, tracks=tracks, library_folder=library_folder, other_folders=other_folders)
        with open(self.path, "r", encoding='utf-8') as f:
            self.include_paths = [line.strip() for line in f]
        self.sanitise_file_paths(library_folder=library_folder, other_folders=other_folders)

    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        if len(self.include_paths) == 0:
            return

        if tracks is None:
            self.tracks = [load_track(path=path) for path in self.include_paths if path is not None]
        else:
            track_paths_map = {track.path.lower(): track for track in tracks}
            tracks = [track_paths_map.get(path.lower()) for path in self.include_paths]
            self.tracks = self.match(tracks)

        return self.tracks

    def write(self, tracks: List[Track]) -> int:
        raise NotImplementedError
