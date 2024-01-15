from abc import ABCMeta, abstractmethod

import pytest

from musify.shared.core.base import Item
from musify.shared.core.misc import PrettyPrinter
from tests.shared.core.misc import PrettyPrinterTester


class ItemTester(PrettyPrinterTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`Item` implementations"""

    @abstractmethod
    def item(self, *args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def item_unequal(self, *args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object that is does not equal the ``item`` being tested"""
        raise NotImplementedError

    @abstractmethod
    def item_modified(self, *args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object that is equal to the ``item`` being tested with some modified values"""
        raise NotImplementedError

    @pytest.fixture
    def obj(self, item: Item) -> PrettyPrinter:
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
    def test_getitem_dunder_method(item: Item):
        assert item["name"] == item.name
        assert item["uri"] == item.uri
