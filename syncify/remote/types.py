from dataclasses import dataclass

from syncify.remote.library.collection import RemoteAlbum
from syncify.remote.library.item import RemoteTrack
from syncify.remote.library.playlist import RemotePlaylist


@dataclass
class RemoteObjectClasses:
    """Stores the key object classes for a remote source"""
    track: type[RemoteTrack]
    album: type[RemoteAlbum]
    playlist: type[RemotePlaylist]
