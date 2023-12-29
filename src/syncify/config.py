from collections.abc import Mapping
from dataclasses import dataclass

from syncify.remote.api import RemoteAPI
from syncify.remote.library import RemoteObject
from syncify.remote.library.library import RemoteLibrary
from syncify.remote.processors.check import RemoteItemChecker
from syncify.remote.processors.search import RemoteItemSearcher
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.spotify import SPOTIFY_SOURCE_NAME
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.library import SpotifyObject
from syncify.spotify.library.library import SpotifyLibrary
from syncify.spotify.processors.processors import SpotifyItemChecker, SpotifyItemSearcher
from syncify.spotify.processors.wrangle import SpotifyDataWrangler


@dataclass
class RemoteClasses:
    """Stores the key classes for a remote source"""
    name: str
    api: type[RemoteAPI]
    wrangler: type[RemoteDataWrangler]
    object: type[RemoteObject]
    library: type[RemoteLibrary]
    checker: type[RemoteItemChecker]
    searcher: type[RemoteItemSearcher]


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
