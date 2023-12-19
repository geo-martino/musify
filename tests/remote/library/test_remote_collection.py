from abc import ABCMeta, abstractmethod
from collections.abc import Iterable

import pytest

from syncify.local.track import LocalTrack
from syncify.remote.library.base import RemoteItem
from syncify.remote.library.collection import RemoteCollection
from tests.abstract.collection import ItemCollectionTester
from tests.local.utils import random_tracks


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
    def test_getitem_dunder_method(collection: RemoteCollection):
        """:py:class:`ItemCollection` __getitem__ and __setitem__ tests"""
        item = collection.items[2]

        assert collection[1] == collection.items[1]
        assert collection[2] == collection.items[2]
        assert collection[:2] == collection.items[:2]

        assert collection[item.name] == item
        assert collection[item.uri] == item
