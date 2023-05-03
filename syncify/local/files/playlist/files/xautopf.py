from typing import Any, List, Mapping, Optional, Set

import xmltodict

from syncify.local.files.playlist.playlist import Playlist
from syncify.local.files.track.collection.collection import TrackCollection
from syncify.local.files.track.tags import PropertyNames
from syncify.local.files.track.track import Track


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
            path: str,
            tracks: List[Track],
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None
    ):
        with open(self.path, "r", encoding='utf-8') as f:
            self.xml: Mapping[str, Any] = xmltodict.parse(f.read())

        collection = TrackCollection.from_xml(xml=self.xml)
        collection.sanitise_file_paths(library_folder=library_folder, other_folders=other_folders)
        TrackCollection.__init__(self)
        self.inherit(collection)

        Playlist.__init__(self, path=path, tracks=tracks, library_folder=library_folder, other_folders=other_folders)
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

        track_paths_map = {track.path.lower(): track for track in tracks}
        tracks = [track_paths_map.get(path.lower()) for path in self.include_paths]

        self.sort_by_field(tracks, field=PropertyNames.LAST_PLAYED, reverse=True)
        tracks = self.match(tracks, reference=tracks[0])
        self.limit(tracks)
        self.sort(tracks)

        return tracks

    def write(self, tracks: List[Track]) -> int:
        raise NotImplementedError
