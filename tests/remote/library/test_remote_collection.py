from abc import ABCMeta, abstractmethod
from collections.abc import Iterable

import pytest

from syncify.local.track import LocalTrack
from syncify.remote.library.collection import RemoteCollection
from syncify.remote.library.item import RemoteItem
from tests.abstract.collection import ItemCollectionTester
from tests.local.utils import random_tracks
from tests.utils import random_str


class RemoteCollectionTester(ItemCollectionTester, metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def collection_merge_items(*args, **kwargs) -> Iterable[RemoteItem]:
        raise NotImplementedError

    @staticmethod
    @pytest.fixture(scope="module")
    def collection_merge_invalid(*args, **kwargs) -> Iterable[LocalTrack]:
        return random_tracks()

    @staticmethod
    def test_getitem_dunder_method(collection: RemoteCollection, collection_merge_items: Iterable[RemoteItem]):
        """:py:class:`ItemCollection` __getitem__ and __setitem__ tests"""
        item = collection.items[2]

        assert collection[1] == collection.items[1]
        assert collection[2] == collection.items[2]
        assert collection[:2] == collection.items[:2]

        assert collection[item] == item
        assert collection[item.name] == item
        assert collection[item.uri] == item
        assert collection[item.id] == item
        assert collection[item.url] == item
        assert collection[item.url_ext] == item

        invalid_item = next(item for item in collection_merge_items)
        with pytest.raises(KeyError):
            assert collection[invalid_item]
        with pytest.raises(KeyError):
            assert collection[invalid_item.name]
        with pytest.raises(KeyError):
            assert collection[invalid_item.uri]
        with pytest.raises(KeyError):
            assert collection[invalid_item.id]
        with pytest.raises(KeyError):
            assert collection[invalid_item.url]
        with pytest.raises(KeyError):
            assert collection[invalid_item.url_ext]

        with pytest.raises(KeyError):
            assert collection[item.remote_source]

