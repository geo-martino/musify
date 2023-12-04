from syncify.remote.processors.check import RemoteItemChecker
from syncify.remote.processors.search import RemoteItemSearcher
from syncify.remote.types import RemoteObjectClasses
from syncify.spotify.library.collection import SpotifyAlbum
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.library.playlist import SpotifyPlaylist
from syncify.spotify.processors.wrangle import SpotifyDataWrangler

__SPOTIFY_OBJECT_TYPES__ = RemoteObjectClasses(
    track=SpotifyTrack, album=SpotifyAlbum, playlist=SpotifyPlaylist
)


class SpotifyProcessor:
    """Generic base class for Spotify processors."""
    @property
    def _remote_types(self) -> RemoteObjectClasses:
        return __SPOTIFY_OBJECT_TYPES__


class SpotifyItemChecker(SpotifyProcessor, SpotifyDataWrangler, RemoteItemChecker):
    pass


class SpotifyItemSearcher(SpotifyProcessor, SpotifyDataWrangler, RemoteItemSearcher):
    pass