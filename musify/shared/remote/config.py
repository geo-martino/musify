from dataclasses import dataclass

from musify.shared.remote.object import RemoteTrack, RemoteAlbum, RemotePlaylist, RemoteArtist


@dataclass
class RemoteObjectClasses:
    """Stores the key object classes for a remote source"""
    playlist: type[RemotePlaylist]
    track: type[RemoteTrack]
    album: type[RemoteAlbum]
    artist: type[RemoteArtist]
