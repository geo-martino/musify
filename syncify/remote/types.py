from dataclasses import dataclass

from .library.collection import RemoteAlbum
from .library.item import RemoteTrack
from .library.playlist import RemotePlaylist


@dataclass
class RemoteObjectClasses:
    """Stores the key object classes for a remote source"""
    track: type[RemoteTrack]
    album: type[RemoteAlbum]
    playlist: type[RemotePlaylist]
