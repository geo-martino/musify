"""
Implements the :py:mod:`Remote` module for Spotify.
"""

from ._base import SpotifyRemote

# noinspection PyTypeChecker
SPOTIFY_NAME: str = SpotifyRemote.source
SPOTIFY_UNAVAILABLE_URI = "spotify:track:unavailable"

# all remote URLs
URL_AUTH = "https://accounts.spotify.com"
URL_API = "https://api.spotify.com/v1"
URL_EXT = "https://open.spotify.com"
