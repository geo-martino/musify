from copy import deepcopy
from collections.abc import Iterable, Collection

import pytest

from local.collection import LocalCollection
from syncify.abstract.item import Item
from syncify.abstract.collection import ItemCollection, BasicCollection, Library


def item_collection_tests(collection: ItemCollection, merge_items: Collection[Item]) -> None:
    """
    Run generic tests on any :py:class:`ItemCollection`.
    The collection must have 3 or more items and all items must be unique.
    You must also provide a set of ``merge_items`` of the same items with different properties
    to merge with the collection.
    """
    assert len(collection.items) >= 3

    collection_basic_operation_tests(collection, merge_items=merge_items)
    collection_basic_dunder_tests(collection)
    collection_iterator_and_container_tests(collection, merge_items=merge_items)
    collection_get_and_set_tests(collection)
    collection_sort_tests(collection)
    collection_merge_tests(collection, merge_items=merge_items)
    collection_delete_and_clear_tests(collection)


def collection_basic_operation_tests(collection: ItemCollection, merge_items: Collection[Item]) -> None:
    """:py:class:`ItemCollection` basic list operation tests"""
    collection = deepcopy(collection)

    index = 2
    item = collection.items[index]
    count_start = collection.items.count(item)
    length_start = len(collection.items)

    assert collection.index(item) == index
    with pytest.raises(ValueError):
        collection.index(item, 0, 1)

    assert collection.count(item) == count_start

    collection.append(item)
    assert len(collection) == length_start + 1
    assert collection.count(item) == count_start + 1
    collection.append(item, allow_duplicates=False)
    assert len(collection) == length_start + 1

    collection.extend(collection)
    assert len(collection) == (length_start + 1) * 2
    assert collection.count(item) == (count_start + 1) * 2
    collection.extend(collection, allow_duplicates=False)
    assert len(collection) == (length_start + 1) * 2

    collection.insert(index - 1, item)
    assert collection.index(item) == index - 1
    collection.insert(0, item, allow_duplicates=False)
    assert collection.index(item) == index - 1

    collection.remove(item)
    assert collection.index(item) == index
    assert collection.pop(index) == item
    assert collection.index(item) > index
    assert collection.pop() is not None


def collection_basic_dunder_tests(collection: ItemCollection) -> None:
    """:py:class:`ItemCollection` basic dunder operation tests"""
    collection = deepcopy(collection)
    collection_original = deepcopy(collection)
    collection_basic = BasicCollection(name="this is a basic collection", items=collection.items)

    assert len(collection) == len(collection.items)

    # math dunder operations
    collection += collection
    assert len(collection) == len(collection_original) * 2

    assert hash(collection) == hash(collection)
    assert hash(collection) != hash(collection_original)
    assert hash(collection) != hash(collection_basic)
    assert collection == collection
    assert collection != collection_original
    assert collection != collection_basic


def collection_iterator_and_container_tests(collection: ItemCollection, merge_items: Iterable[Item]) -> None:
    """:py:class:`ItemCollection` dunder iterator and contains tests"""
    collection = deepcopy(collection)

    assert all(isinstance(item, Item) for item in collection)
    assert len([item for item in collection]) == len(collection)
    assert len([item for item in reversed(collection)]) == len(collection)
    for i, item in enumerate(reversed(collection)):
        print(i, collection.index(item), len(collection) - 1 - i)
        assert collection.index(item) == len(collection) - 1 - i

    assert all(item in collection for item in collection)
    assert all(item not in collection for item in merge_items)


def collection_get_and_set_tests(collection: ItemCollection) -> None:
    """:py:class:`ItemCollection` __getitem__ and __setitem__ tests"""
    collection = deepcopy(collection)

    item = collection.items[2]
    assert collection[1] == collection.items[1]
    assert collection[2] == collection.items[2]
    assert collection[item.name] == item
    if collection.remote_wrangler is not None:
        assert collection[item.uri] == item
    if isinstance(collection, LocalCollection):
        assert collection[item.path] == item

    # __setitem__
    item = next(i for i in collection[1:] if isinstance(i, type(collection[0])))
    assert collection.index(item) > 0
    collection[0] = item
    assert collection.index(item) == 0
    with pytest.raises(IndexError):
        collection[len(collection) + 5] = item


def collection_sort_tests(collection: ItemCollection) -> None:
    """:py:class:`ItemCollection` sorting tests"""
    collection = deepcopy(collection)

    start_items = collection.copy()
    collection.reverse()
    assert collection == list(reversed(start_items))
    collection.sort(reverse=True)
    assert collection == start_items


def collection_merge_tests(collection: ItemCollection, merge_items: Collection[Item]) -> None:
    """:py:class:`ItemCollection` merge items tests"""
    collection = deepcopy(collection)
    length = len(collection.items)

    assert all(item not in collection for item in merge_items)
    collection.merge_items(merge_items)
    assert len(collection.items) == length


def collection_delete_and_clear_tests(collection: ItemCollection) -> None:
    """:py:class:`ItemCollection` __delitem__ and clear tests"""
    collection = deepcopy(collection)
    item = collection.items[2]

    del collection[item]
    assert item not in collection
    collection.clear()
    assert len(collection) == 0


def library_tests(library: Library) -> None:
    """
    Run generic tests on any :py:class:`Library`.
    The collection must have 3 or more playlists and all playlists must be unique.
    """
    assert len(library.playlists) >= 3

    library_filtered_playlists_tests(library)
    library_merge_playlists_tests(library)


def library_filtered_playlists_tests(library: Library) -> None:
    """:py:class:`Library` `get_filtered_playlists` tests"""
    include = [name for name in library.playlists][:1]
    pl_include = library.get_filtered_playlists(include=include)
    assert len(pl_include) == len(include)
    assert all(pl.name in include for pl in pl_include.values())

    exclude = [name for name in library.playlists][:1]
    pl_exclude = library.get_filtered_playlists(exclude=exclude)
    assert len(pl_exclude) == len(library.playlists) - len(exclude)
    assert all(pl.name not in exclude for pl in pl_exclude.values())

    # exclude should always take priority
    assert len(library.get_filtered_playlists(include=include, exclude=include)) == 0

    # TODO: add filter_kwargs test


def library_merge_playlists_tests(library: Library) -> None:
    """:py:class:`Library` `merge_playlists` tests"""
    # TODO: write tests
    pass
