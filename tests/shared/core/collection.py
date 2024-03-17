from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from copy import deepcopy

import pytest

from musify.processors.filter import FilterDefinedList, FilterIncludeExclude
from musify.shared.core.base import MusifyItem
from musify.shared.core.collection import MusifyCollection
from musify.shared.core.misc import PrettyPrinter
from musify.shared.core.object import BasicCollection, Library, Playlist
from musify.shared.exception import MusifyTypeError
from musify.shared.remote.library import RemoteLibrary
from musify.shared.remote.object import RemoteCollectionLoader
from tests.shared.core.misc import PrettyPrinterTester


class ItemCollectionTester(PrettyPrinterTester, metaclass=ABCMeta):
    """
    Run generic tests for :py:class:`ItemCollection` implementations.
    The collection must have 3 or more items and all items must be unique.
    You must also provide a set of ``merge_items`` of the same items with different properties
    to merge with the collection.
    """

    dict_json_equal = False

    @abstractmethod
    def collection(self, *args, **kwargs) -> MusifyCollection:
        """Yields an :py:class:`ItemCollection` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[MusifyItem]:
        """Yields an Iterable of :py:class:`Item` for use in :py:class:`ItemCollection` tests as pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def collection_merge_invalid(self, *args, **kwargs) -> Iterable[MusifyItem]:
        """Yields an Iterable of :py:class:`Item` for use in :py:class:`ItemCollection` tests as pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def obj(self, collection: MusifyCollection) -> PrettyPrinter:
        return collection

    @staticmethod
    def test_collection_input_validation(collection: MusifyCollection, collection_merge_invalid: Iterable[MusifyItem]):
        with pytest.raises(MusifyTypeError):
            collection.index(next(c for c in collection_merge_invalid))
        with pytest.raises(MusifyTypeError):
            collection.count(next(c for c in collection_merge_invalid))
        with pytest.raises(MusifyTypeError):
            collection.append(next(c for c in collection_merge_invalid))
        with pytest.raises(MusifyTypeError):
            collection.insert(0, next(c for c in collection_merge_invalid))

        if not isinstance(collection, RemoteLibrary):  # overriden by remote libraries
            with pytest.raises(MusifyTypeError):
                collection.extend(collection_merge_invalid)
            with pytest.raises(MusifyTypeError):
                collection += collection_merge_invalid

    @staticmethod
    def test_collection_mutable_sequence_methods(collection: MusifyCollection):
        assert len(collection.items) >= 3

        # get a unique item and its index
        index, item = next(
            (i, item) for i, item in enumerate(collection.items[1:], 1) if collection.items.count(item) == 1
        )
        length_start = len(collection.items)

        assert collection.count(item) == 1
        assert collection.items == collection.copy()

        assert collection.index(item) == index
        with pytest.raises(ValueError):
            collection.index(collection.items[2], 0, 1)

        collection.append(item)
        assert len(collection) == length_start + 1
        assert collection.count(item) == 2
        collection.append(item, allow_duplicates=False)
        assert len(collection) == length_start + 1

        if not isinstance(collection, RemoteLibrary):  # overriden by remote libraries
            collection.extend(collection)
            assert len(collection) == (length_start + 1) * 2
            assert collection.count(item) == 4
            collection.extend(collection, allow_duplicates=False)
            assert len(collection) == (length_start + 1) * 2
        else:
            collection.items.extend(collection.items)
            assert len(collection) == (length_start + 1) * 2

        collection.insert(index - 1, item)
        assert collection.index(item) == index - 1
        collection.insert(0, item, allow_duplicates=False)
        assert collection.index(item) == index - 1

        collection.remove(item)
        assert collection.index(item) == index
        assert collection.pop(index) == item
        assert collection.items[index] != item
        assert collection.pop() is not None

        collection.clear()
        assert len(collection) == 0

    @staticmethod
    def test_collection_basic_dunder_methods(collection: MusifyCollection):
        """:py:class:`ItemCollection` basic dunder operation tests"""
        collection_original = deepcopy(collection)
        collection_basic = BasicCollection(name="this is a basic collection", items=collection.items)

        assert len(collection) == len(collection.items)

        assert collection == collection
        assert collection == collection_original
        assert collection != collection_basic

        # math dunder operations
        assert collection + collection == collection.items + collection.items
        assert collection - collection == []

        collection.items.extend(collection.items)
        assert len(collection) == len(collection_original) * 2 == len(collection.items)
        if isinstance(collection, RemoteCollectionLoader):  # these match on URIs so always equal no matter what
            assert collection == collection_original
        else:
            assert collection != collection_original

        collection -= collection_original
        assert len(collection) == len(collection_original) == len(collection.items)
        assert collection == collection_original

    @staticmethod
    def test_collection_iterator_and_container_dunder_methods(
            collection: MusifyCollection, collection_merge_items: Iterable[MusifyItem]
    ):
        """:py:class:`ItemCollection` dunder iterator and contains tests"""
        assert len([item for item in collection]) == len(collection.items)
        assert len([item for item in reversed(collection.items)]) == len(collection.items)
        for i, item in enumerate(reversed(collection.items)):
            assert collection.items.index(item) == len(collection.items) - 1 - i

        assert all(item in collection for item in collection.items)
        assert all(item not in collection.items for item in collection_merge_items)

    @abstractmethod
    def test_collection_getitem_dunder_method(
            self, collection: MusifyCollection, collection_merge_items: Iterable[MusifyItem]
    ):
        raise NotImplementedError

    @staticmethod
    def test_collection_setitem_dunder_method(collection: MusifyCollection):
        classes = [item.__class__ for item in collection]
        idx_1, item_1 = next((i, item) for i, item in enumerate(collection.items) if classes.count(item.__class__) > 1)
        idx_2, item_2 = next(
            (i, item) for i, item in enumerate(collection.items[idx_1+1:], idx_1+1)
            if item.__class__ == item_1.__class__
        )

        assert idx_1 < idx_2
        assert item_1 != item_2
        assert collection[idx_1] != collection[idx_2]
        assert collection.items.index(item_1) == idx_1
        assert collection.items.index(item_2) == idx_2

        collection[idx_1] = item_2
        assert collection.items.index(item_2) == idx_1
        with pytest.raises(IndexError):  # does not set items outside of max length range
            collection[len(collection.items) + 5] = item_1

    @staticmethod
    def test_collection_delitem_dunder_method(collection: MusifyCollection):
        item = next(i for i in collection.items if collection.items.count(i) == 1)

        del collection[item]
        assert item not in collection

    @staticmethod
    def test_collection_sort(collection: MusifyCollection):
        items = collection.items.copy()

        collection.reverse()
        assert collection == list(reversed(items))

        collection.sort(reverse=True)
        assert collection == items


class PlaylistTester(ItemCollectionTester, metaclass=ABCMeta):

    @abstractmethod
    def playlist(self, *args, **kwargs) -> Playlist:
        """Yields an :py:class:`Playlist` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def collection(self, playlist: Playlist) -> MusifyCollection:
        return playlist

    @pytest.mark.skip(reason="not implemented yet")
    def test_merge(self, playlist: Playlist):
        pass

    @pytest.mark.skip(reason="not implemented yet")
    def test_merge_dunder_methods(self, playlist: Playlist):
        pass


class LibraryTester(ItemCollectionTester, metaclass=ABCMeta):
    """
    Run generic tests for :py:class:`Library` implementations.
    The collection must have 3 or more playlists and all playlists must be unique.
    """

    @abstractmethod
    def library(self, *args, **kwargs) -> Library:
        """Yields a loaded :py:class:`Library` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def collection(self, library: Library) -> MusifyCollection:
        return library

    @staticmethod
    def test_get_filtered_playlists_basic(library: Library):
        include = FilterDefinedList([name for name in library.playlists][:1])
        pl_include = library.get_filtered_playlists(playlist_filter=include)
        assert len(pl_include) == len(include) < len(library.playlists)
        assert all(pl.name in include for pl in pl_include.values())

        exclude = FilterIncludeExclude(
            include=FilterDefinedList(),
            exclude=FilterDefinedList([name for name in library.playlists][:1])
        )
        pl_exclude = library.get_filtered_playlists(playlist_filter=exclude)
        assert len(pl_exclude) == len(library.playlists) - len(exclude.exclude.values) < len(library.playlists)
        assert all(pl.name not in exclude for pl in pl_exclude.values())

    @staticmethod
    def test_get_filtered_playlists_on_tags(library: Library):
        # filters out tags
        filter_names = [item.name for item in next(pl for pl in library.playlists.values() if len(pl) > 0)[:2]]
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

    @abstractmethod
    def test_merge_playlists(self, library: Library):
        raise NotImplementedError
