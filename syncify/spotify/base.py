from syncify.remote.base import Remote
from syncify.spotify import SPOTIFY_SOURCE_NAME


class SpotifyRemote(Remote):
    """Base class for any object concerning Spotify functionality"""

    @property
    def remote_source(self) -> str:
        return SPOTIFY_SOURCE_NAME
