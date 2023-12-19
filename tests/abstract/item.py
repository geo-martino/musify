from abc import ABCMeta, abstractmethod
from copy import copy

import pytest

from syncify.abstract.item import Item
from syncify.abstract.misc import PrettyPrinter
from syncify.remote.library.item import RemoteItem
from tests.abstract.misc import PrettyPrinterTester
from tests.spotify.utils import random_uri


class ItemTester(PrettyPrinterTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`Item` implementations"""

    @staticmethod
    @abstractmethod
    def item(*args, **kwargs) -> Item:
        """Yields an :py:class:`Item` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @staticmethod
    @pytest.fixture
    def obj(item: Item) -> PrettyPrinter:
        return item

    @staticmethod
    def test_equality(item: Item):
        assert hash(item) == hash(item)
        assert item == item

        # TODO: add fixture for item_modified and make item_modified a different type for each ItemTester implementation
        if isinstance(item, RemoteItem):
            return

        item_modified = copy(item)
        item_modified.uri = random_uri()

        assert hash(item) != hash(item_modified)
        assert item == item_modified  # still matches on path

    @staticmethod
    def test_get_attributes(item: Item):
        assert item["name"] == item.name
        assert item["uri"] == item.uri

    @staticmethod
    def test_set_attributes(item: Item):
        # TODO: make this abstract, implement at module level for local and item level for remote
        if isinstance(item, RemoteItem):
            return

        assert item.uri != "new_uri"
        item["uri"] = "new_uri"
        assert item.uri == "new_uri"

        with pytest.raises(KeyError):
            item["bad key"] = "value"

        with pytest.raises(AttributeError):
            item["name"] = "cannot set name"

    @staticmethod
    def test_merge_item(item: Item):
        """:py:class:`Item` `merge` tests"""
        # TODO: add fixture for item_modified and make item_modified a different type for each ItemTester implementation
        if isinstance(item, RemoteItem):
            return

        item_modified = copy(item)
        item_modified.uri = "new_uri"

        assert item.uri != item_modified.uri
        item.merge(item_modified)
        assert item.uri == item_modified.uri
