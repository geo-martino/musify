from musify.shared.remote.config import RemoteObjectClasses
from musify.shared.remote.processors.check import RemoteItemChecker
from musify.shared.remote.processors.search import RemoteItemSearcher
from musify.spotify.config import SPOTIFY_OBJECT_CLASSES
from musify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyItemChecker(SpotifyDataWrangler, RemoteItemChecker):
    @property
    def _object_cls(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_CLASSES


class SpotifyItemSearcher(SpotifyDataWrangler, RemoteItemSearcher):
    @property
    def _object_cls(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_CLASSES
