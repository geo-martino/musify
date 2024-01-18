"""
Configuration relating to the :py:mod:`Spotify` module.

This configuration can be used to inject dependencies into dependencies throughout the module.
"""

from musify.shared.remote.config import RemoteObjectClasses
from musify.spotify.object import SpotifyPlaylist, SpotifyTrack, SpotifyAlbum, SpotifyArtist

SPOTIFY_OBJECT_CLASSES = RemoteObjectClasses(
    playlist=SpotifyPlaylist,
    track=SpotifyTrack,
    album=SpotifyAlbum,
    artist=SpotifyArtist,
)
