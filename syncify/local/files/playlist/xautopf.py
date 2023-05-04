from typing import Any, List, Mapping, Optional, Set

import xmltodict

from syncify.local.files import TrackMatch, TrackLimit, TrackSort
from syncify.local.files.track import PropertyName, Track
from syncify.local.files.playlist import Playlist


class XAutoPF(Playlist):
    """
    For reading and writing data from MusicBee's auto-playlist format.

    **Note**: You must provide a list of tracks to search on initialisation for this playlist type.

    :param path: Full path of the playlist.
    :param tracks: Available Tracks to search through for matches. Required.
    :param library_folder: Full path of folder containing tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    playlist_ext = [".xautopf"]

    def __init__(
            self,
            path: Optional[str],
            tracks: List[Track],
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None
    ):
        with open(path, "r", encoding='utf-8') as f:
            self.xml: Mapping[str, Any] = xmltodict.parse(f.read())

        Playlist.__init__(
            self,
            path=path,
            tracks=tracks,
            library_folder=library_folder,
            other_folders=other_folders,
            matcher=TrackMatch.from_xml(xml=self.xml),
            limiter=TrackLimit.from_xml(xml=self.xml),
            sorter=TrackSort.from_xml(xml=self.xml)
        )
        self.description = self.xml["SmartPlaylist"]["Source"]["Description"]

    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        """
        Read the playlist file.

        **Note**: You must provide a list of tracks for this playlist type.

        :param tracks: Available Tracks to search through for matches.
        :return: Ordered list of tracks in this playlist
        """
        if tracks is None:
            raise ValueError("This playlist type requires that you provide a list of loaded tracks")

        if self.include_paths is not None:
            include_paths_original = self.include_paths.copy()
            include_paths_lower = {path.lower() for path in self.include_paths}
            self.include_paths = {track.path for track in tracks if track.path.lower() in include_paths_lower}

        if self.exclude_paths is not None:
            exclude_paths_original = self.include_paths.copy()
            exclude_paths_lower = {path.lower() for path in self.exclude_paths}
            self.exclude_paths = {track.path for track in tracks if track.path.lower() in exclude_paths_lower}

        self.sort_by_field(tracks, field=PropertyName.LAST_PLAYED, reverse=True)
        self.tracks = self.match(tracks, reference=tracks[0])
        self.limit(self.tracks)
        self.sort(self.tracks)

        if self.include_paths is not None:
            self.include_paths = include_paths_original
        if self.exclude_paths is not None:
            self.exclude_paths = exclude_paths_original

        return tracks

    def write(self, tracks: List[Track]) -> int:
        raise NotImplementedError


if __name__ == "__main__":
    from syncify.local.files.track import FLAC
    from syncify.local.files.track import MP3
    from syncify.local.files.track import M4A
    from syncify.local.files.track import WMA
    from syncify.local.files import load_track

    from os.path import join

    playlist_folder = join("MusicBee", "Playlists")
    library_folder = "D:\\Music\\"
    other_folder = "/mnt/d/Music/"

    print("Setting file paths")
    FLAC.set_file_paths(library_folder=library_folder)
    MP3.set_file_paths(library_folder=library_folder)
    M4A.set_file_paths(library_folder=library_folder)
    WMA.set_file_paths(library_folder=library_folder)

    print("Loading tracks")
    tracks = []
    tracks.extend(load_track(path=path) for path in FLAC.available_track_paths)
    tracks.extend(load_track(path=path) for path in MP3.available_track_paths)
    tracks.extend(load_track(path=path) for path in M4A.available_track_paths)
    tracks.extend(load_track(path=path) for path in WMA.available_track_paths)

    name = "70s.xautopf"
    path = join(library_folder, playlist_folder, name)

    pl = XAutoPF(path=path, tracks=tracks, library_folder=library_folder, other_folders={other_folder})

    [print(str(i).zfill(3), track.album, track.title, sep=" = ") for i, track in enumerate(pl.tracks, 1)]
