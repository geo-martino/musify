from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any

from syncify.spotify.library.base import SpotifyObject, SpotifyItem
from tests.remote.library.test_remote_collection import RemoteCollectionTester


def assert_id_attributes(item: SpotifyObject, response: dict[str, Any]):
    """Check a given :py:class:`SpotifyObject` has the expected attributes relating to its identification"""
    assert item.has_uri
    assert item.uri == response["uri"]
    assert item.id == response["id"]
    assert item.url == response["href"]
    assert item.url_ext == response["external_urls"]["spotify"]


class SpotifyCollectionTester(RemoteCollectionTester, metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def collection_merge_items() -> Iterable[SpotifyItem]:
        raise NotImplementedError

