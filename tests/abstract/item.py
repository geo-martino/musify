from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy

import pytest

from syncify.abstract.item import Item
from syncify.abstract.misc import PrettyPrinter
from syncify.remote.library.item import RemoteItem
from tests.abstract.misc import PrettyPrinterTester
from tests.utils import random_str


class ItemTester(PrettyPrinterTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`Item` implementations"""

    @staticmethod
    @abstractmethod
    def item(*args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def item_unequal(*args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object that is does not equal the ``item`` being tested"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def item_modified(*args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object that is equal to the ``item`` being tested with some modified values"""
        raise NotImplementedError

    @staticmethod
    @pytest.fixture
    def obj(item: Item) -> PrettyPrinter:
        return item

    @staticmethod
    def test_equality(item: Item, item_modified: Item, item_unequal: Item):
        assert hash(item) == hash(item)
        assert item == item

        assert hash(item) == hash(item_modified)
        assert item == item_modified

        assert hash(item) != hash(item_unequal)
        assert item != item_unequal

    @staticmethod
    def test_get_attributes(item: Item):
        assert item["name"] == item.name
        assert item["uri"] == item.uri
