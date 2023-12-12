from dataclasses import dataclass

from .api import RemoteAPI
from .base import RemoteObject
from .library.library import RemoteLibrary
from .processors.check import RemoteItemChecker
from .processors.search import RemoteItemSearcher
from .processors.wrangle import RemoteDataWrangler


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
