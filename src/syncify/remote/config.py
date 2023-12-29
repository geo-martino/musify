from dataclasses import dataclass

from syncify.remote.library.object import RemoteTrack, RemoteAlbum, RemotePlaylist


@dataclass
class RemoteObjectClasses:
    """Stores the key object classes for a remote source"""
    track: type[RemoteTrack]
    album: type[RemoteAlbum]
    playlist: type[RemotePlaylist]
