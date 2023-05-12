from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import List

from syncify.spotify.api import API
from syncify.spotify.library.item import SpotifyItem
from syncify.spotify.processor.match import ItemMatcher


@dataclass
class SearchResult:
    matched: List[SpotifyItem]
    unmatched: List[SpotifyItem]
    skipped: List[SpotifyItem]


class ItemSearcher(ItemMatcher, metaclass=ABCMeta):

    @property
    @abstractmethod
    def api(self) -> API:
        raise NotImplementedError

    def search(self) -> SearchResult:
        pass
