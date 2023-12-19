from dataclasses import dataclass

from syncify.remote.library.collection import RemoteAlbum, RemotePlaylist
from syncify.remote.library.item import RemoteTrack


@dataclass
class RemoteObjectClasses:
    """Stores the key object classes for a remote source"""
    track: type[RemoteTrack]
    album: type[RemoteAlbum]
    playlist: type[RemotePlaylist]
