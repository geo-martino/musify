"""
Configuration relating to the :py:mod:`Remote` module.

This configuration can be used to inject dependencies into dependencies throughout the module.
"""

from dataclasses import dataclass

from musify.shared.remote.object import RemoteTrack, RemoteAlbum, RemotePlaylist, RemoteArtist


@dataclass
class RemoteObjectClasses:
    """Stores the key object classes for a remote source"""
    #: The playlist type for this remote source
    playlist: type[RemotePlaylist]
    #: The track type for this remote source
    track: type[RemoteTrack]
    #: The album type for this remote source
    album: type[RemoteAlbum]
    #: The artist type for this remote source
    artist: type[RemoteArtist]
