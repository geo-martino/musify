from syncify.remote.config import RemoteObjectClasses
from syncify.remote.processors.check import RemoteItemChecker
from syncify.remote.processors.search import RemoteItemSearcher
from syncify.spotify.config import SPOTIFY_OBJECT_CLASSES
from syncify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyItemChecker(SpotifyDataWrangler, RemoteItemChecker):
    @property
    def _object_cls(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_CLASSES


class SpotifyItemSearcher(SpotifyDataWrangler, RemoteItemSearcher):
    @property
    def _object_cls(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_CLASSES
