from collections.abc import Mapping

from syncify.remote.config import RemoteClasses
from syncify.spotify import __SPOTIFY_SOURCE_NAME__
from syncify.spotify.api.api import SpotifyAPI
from syncify.spotify.base import SpotifyObject
from syncify.spotify.library.library import SpotifyLibrary
from syncify.spotify.processors.processors import SpotifyItemChecker, SpotifyItemSearcher
from syncify.spotify.processors.wrangle import SpotifyDataWrangler

# map of the names of all supported remote sources and their associated implementations
__REMOTE_CONFIG__: Mapping[str, RemoteClasses] = {
    __SPOTIFY_SOURCE_NAME__.casefold().strip(): RemoteClasses(
        name=__SPOTIFY_SOURCE_NAME__,
        api=SpotifyAPI,
        wrangler=SpotifyDataWrangler,
        object=SpotifyObject,
        library=SpotifyLibrary,
        checker=SpotifyItemChecker,
        searcher=SpotifyItemSearcher,
    )
}
