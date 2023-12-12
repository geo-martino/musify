from syncify.remote.processors.check import RemoteItemChecker
from syncify.remote.processors.search import RemoteItemSearcher
from syncify.remote.types import RemoteObjectClasses
from syncify.spotify.library.collection import SpotifyAlbum
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.library.playlist import SpotifyPlaylist
from .wrangle import SpotifyDataWrangler

SPOTIFY_OBJECT_TYPES = RemoteObjectClasses(
    track=SpotifyTrack, album=SpotifyAlbum, playlist=SpotifyPlaylist
)


class SpotifyProcessor:
    """Generic base class for Spotify processors."""
    @property
    def _remote_types(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_TYPES


class SpotifyItemChecker(SpotifyProcessor, SpotifyDataWrangler, RemoteItemChecker):
    pass


class SpotifyItemSearcher(SpotifyProcessor, SpotifyDataWrangler, RemoteItemSearcher):
    pass
