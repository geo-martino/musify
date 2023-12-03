from dataclasses import dataclass

from syncify.remote.api.api import RemoteAPI
from syncify.remote.base import RemoteObject
from syncify.remote.library.library import RemoteLibrary
from syncify.remote.processors.check import RemoteItemChecker
from syncify.remote.processors.search import RemoteItemSearcher
from syncify.remote.processors.wrangle import RemoteDataWrangler


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
