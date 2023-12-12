from collections.abc import Mapping

from .remote.config import RemoteClasses
from .spotify import SPOTIFY_SOURCE_NAME
from .spotify.api import SpotifyAPI
from .spotify.base import SpotifyObject
from .spotify.library.library import SpotifyLibrary
from .spotify.processors.processors import SpotifyItemChecker, SpotifyItemSearcher
from .spotify.processors.wrangle import SpotifyDataWrangler

# map of the names of all supported remote sources and their associated implementations
REMOTE_CONFIG: Mapping[str, RemoteClasses] = {
    SPOTIFY_SOURCE_NAME.casefold().strip(): RemoteClasses(
        name=SPOTIFY_SOURCE_NAME,
        api=SpotifyAPI,
        wrangler=SpotifyDataWrangler,
        object=SpotifyObject,
        library=SpotifyLibrary,
        checker=SpotifyItemChecker,
        searcher=SpotifyItemSearcher,
    )
}
