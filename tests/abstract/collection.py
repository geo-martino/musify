from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Collection
from copy import deepcopy

import pytest

from syncify.abstract.collection import ItemCollection, BasicCollection, Library
from syncify.abstract.item import Item
from syncify.abstract.misc import PrettyPrinter
from syncify.local.collection import LocalCollection
from tests.abstract.misc import PrettyPrinterTester


class ItemCollectionTester(PrettyPrinterTester, metaclass=ABCMeta):
    """
    Run generic tests for :py:class:`ItemCollection` implementations.
    The collection must have 3 or more items and all items must be unique.
    You must also provide a set of ``merge_items`` of the same items with different properties
    to merge with the collection.
    """

    @staticmethod
    @abstractmethod
    def collection(*args, **kwargs) -> ItemCollection:
        """Yields an :py:class:`ItemCollection` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def collection_merge_items(*args, **kwargs) -> Iterable[Item]:
        """Yields an Iterable of :py:class:`Item` for use in :py:class:`ItemCollection` tests as pytest.fixture"""
        raise NotImplementedError

    @staticmethod
    @pytest.fixture
    def obj(collection: ItemCollection) -> PrettyPrinter:
        return collection

    @staticmethod
    def test_mutable_sequence_methods(collection: ItemCollection):
        assert len(collection.items) >= 3

        index = 2
        item = collection.items[index]
        count_start = collection.items.count(item)
        length_start = len(collection.items)

        assert collection.index(item) == index
        with pytest.raises(ValueError):
            collection.index(item, 0, 1)

        assert collection.count(item) == count_start
        assert collection.items == collection.copy()

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

        collection.clear()
        assert len(collection) == 0

    @staticmethod
    def test_basic_dunder_methods(collection: ItemCollection):
        """:py:class:`ItemCollection` basic dunder operation tests"""
        collection_original = deepcopy(collection)
        collection_basic = BasicCollection(name="this is a basic collection", items=collection.items)

        assert len(collection) == len(collection.items)

        assert hash(collection) == hash(collection)
        assert hash(collection) == hash(collection_original)
        assert hash(collection) != hash(collection_basic)
        assert collection == collection
        assert collection == collection_original
        assert collection != collection_basic

        # math dunder operations
        collection += collection
        assert len(collection) == len(collection_original) * 2 == len(collection.items)

        assert hash(collection) != hash(collection_original)
        assert collection != collection_original

    @staticmethod
    def test_iterator_and_container_dunder_methods(collection: ItemCollection, collection_merge_items: Iterable[Item]):
        """:py:class:`ItemCollection` dunder iterator and contains tests"""
        assert all(isinstance(item, Item) for item in collection.items)
        assert len([item for item in collection]) == len(collection.items)
        assert len([item for item in reversed(collection.items)]) == len(collection.items)
        for i, item in enumerate(reversed(collection.items)):
            assert collection.items.index(item) == len(collection.items) - 1 - i

        assert all(item in collection for item in collection.items)
        assert all(item not in collection.items for item in collection_merge_items)

    @staticmethod
    def test_getitem_dunder_method(collection: ItemCollection):
        """:py:class:`ItemCollection` __getitem__ and __setitem__ tests"""
        item = collection.items[2]

        assert collection[1] == collection.items[1]
        assert collection[2] == collection.items[2]
        assert collection[:2] == collection.items[:2]

        assert collection[item.name] == item

        if collection.remote_wrangler is not None:
            assert collection[item.uri] == item
        if isinstance(collection, LocalCollection):  # also check getitem from path
            assert collection[item.path] == item

    @staticmethod
    def test_setitem_dunder_method(collection: ItemCollection):
        item = next(i for i in collection.items[1:] if isinstance(i, type(collection[0])))
        assert collection.items.index(item) > 0

        collection[0] = item
        assert collection.items.index(item) == 0
        with pytest.raises(IndexError):  # does not set items outside of max length range
            collection[len(collection.items) + 5] = item

    @staticmethod
    def test_delitem_dunder_method(collection: ItemCollection):
        item = next(i for i in collection.items if collection.items.count(i) == 1)

        del collection[item]
        assert item not in collection

    @staticmethod
    def test_sort(collection: ItemCollection):
        items = collection.items.copy()

        collection.reverse()
        assert collection == list(reversed(items))

        collection.sort(reverse=True)
        assert collection == items

    @staticmethod
    def test_merge_items(collection: ItemCollection, collection_merge_items: Collection[Item]):
        length = len(collection.items)
        assert all(item not in collection.items for item in collection_merge_items)

        collection.merge_items(collection_merge_items)
        assert len(collection.items) == length


class LibraryTester(ItemCollectionTester, metaclass=ABCMeta):
    """
    Run generic tests for :py:class:`Library` implementations.
    The collection must have 3 or more playlists and all playlists must be unique.
    """

    @abstractmethod
    def library(self, *args, **kwargs) -> Library:
        """Yields an :py:class:`Library` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def collection(self, library: Library) -> ItemCollection:
        return library

    @staticmethod
    def test_get_filtered_playlists_basic(library: Library):
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

    @staticmethod
    def test_get_filtered_playlists_on_tags(library: Library):
        # filters out tags
        filter_names = [item.name for item in next(pl for pl in library.playlists.values())[:2]]
        filter_tags = {"name": [name.upper() + "  " for name in filter_names]}
        expected_counts = {}
        for name, pl in library.playlists.items():
            count_remaining = len([item for item in pl if item.name not in filter_names])
            if count_remaining < len(pl):
                expected_counts[name] = count_remaining

        if len(expected_counts) == 0:
            raise Exception("Can't check filter_tags logic, no items to filter out from playlists")

        filtered_playlists = library.get_filtered_playlists(**filter_tags)
        for name, pl in filtered_playlists.items():
            if name not in expected_counts:
                continue
            assert len(pl) == expected_counts[name]

    @staticmethod
    def test_merge_playlists(library: Library):
        # TODO: write merge_playlists tests
        pass
