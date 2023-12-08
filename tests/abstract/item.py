from copy import copy

import pytest

from syncify.abstract.item import Item
from syncify.local.base import LocalObject
from tests.remote import random_uri


def item_tests(item: Item) -> None:
    """Run generic tests on any :py:class:`Item`."""
    item_basic_dunder_tests(item)
    item_get_and_set_tests(item)
    item_merge_tests(item)


def item_basic_dunder_tests(item: Item) -> None:
    """:py:class:`Item` basic dunder operation tests"""
    item_modified = copy(item)
    item_modified.uri = random_uri()

    assert hash(item) == hash(item)
    assert hash(item) != hash(item_modified)
    assert item == item

    if isinstance(item, LocalObject):
        # still matches on path
        assert item == item_modified
    else:
        assert item != item_modified


def item_get_and_set_tests(item: Item) -> None:
    """:py:class:`Item` __getitem__ and __setitem__ tests"""
    item = copy(item)

    assert item["name"] == item.name
    assert item["uri"] == item.uri

    assert item.uri != "new_uri"
    item["uri"] = "new_uri"
    assert item.uri == "new_uri"

    with pytest.raises(KeyError):
        item["bad key"] = "value"

    with pytest.raises(AttributeError):
        item["name"] = "value"


def item_merge_tests(item: Item) -> None:
    """:py:class:`Item` `merge` tests"""
    item_modified = copy(item)
    item_modified.uri = "new_uri"

    assert item.uri != item_modified.uri
    item.merge(item_modified)
    assert item.uri == item_modified.uri
