from abc import ABC, abstractmethod
from collections.abc import Iterable
from copy import deepcopy
from random import sample
from typing import Any

import pytest

from musify.core.base import MusifyItem
from musify.core.printer import PrettyPrinter
from musify.exception import MusifyTypeError
from musify.libraries.collection import BasicCollection
from musify.libraries.core.collection import MusifyCollection
from musify.libraries.core.object import Library, Playlist, Track
from musify.libraries.remote.core.library import RemoteLibrary
from musify.libraries.remote.core.object import RemoteCollectionLoader
from tests.core.printer import PrettyPrinterTester


class MusifyCollectionTester(PrettyPrinterTester, ABC):
    """
    Run generic tests for :py:class:`MusifyCollection` implementations.
    The collection must have 3 or more items and all items must be unique.
    You must also provide a set of ``merge_items`` of the same items with different properties
    to merge with the collection.
    """

    dict_json_equal = False

    @abstractmethod
    def collection(self, *args, **kwargs) -> MusifyCollection:
        """Yields an :py:class:`MusifyCollection` object to be tested as pytest.fixture."""
        raise NotImplementedError

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[MusifyItem]:
        """
        Yields an Iterable of :py:class:`MusifyItem` for use in :py:class:`MusifyCollection` tests
        as pytest.fixture
        """
        raise NotImplementedError

    @abstractmethod
    def collection_merge_invalid(self, *args, **kwargs) -> Iterable[MusifyItem]:
        """
        Yields an Iterable of :py:class:`MusifyItem` for use in :py:class:`MusifyCollection` tests
        as pytest.fixture
        """
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

        if not isinstance(collection, RemoteLibrary):  # overridden by remote libraries
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

        if not isinstance(collection, RemoteLibrary):  # overridden by remote libraries
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
        """:py:class:`MusifyCollection` basic dunder operation tests"""
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
        """:py:class:`MusifyCollection` dunder iterator and contains tests"""
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

    @staticmethod
    def test_collection_difference_and_intersection(
            collection: MusifyCollection, collection_merge_items: Iterable[MusifyItem]
    ):
        difference = [item for item in collection_merge_items]
        other = collection.items + difference

        assert collection.difference(other) == difference
        assert collection.intersection(other) == collection.items


class PlaylistTester(MusifyCollectionTester, ABC):

    @abstractmethod
    def playlist(self, *args, **kwargs) -> Playlist:
        """Yields an :py:class:`Playlist` object to be tested as pytest.fixture."""
        raise NotImplementedError

    @pytest.fixture
    def collection(self, playlist: Playlist) -> MusifyCollection:
        return playlist

    # noinspection PyTypeChecker
    @staticmethod
    def test_merge_input_validation(playlist: Playlist, collection_merge_invalid: Iterable[MusifyItem]):
        with pytest.raises(MusifyTypeError):
            playlist.merge(collection_merge_invalid)

    @staticmethod
    def test_merge[T: Track](playlist: Playlist[T], collection_merge_items: Iterable[T]):
        initial_count = len(playlist)
        items = [item for item in collection_merge_items]

        playlist.merge([items[0]])
        assert len(playlist) == initial_count + 1
        assert playlist[-1] == items[0]

        playlist.merge(playlist.items + items[:-1])
        assert len(playlist) == initial_count + len(items) - 1

        playlist.merge(playlist.items + items)
        assert len(playlist) == initial_count + len(items)

    @staticmethod
    def test_merge_with_reference[T: Track](playlist: Playlist[T], collection_merge_items: Iterable[T]):
        # setup collections so 2 items are always removed and many items are always added
        reference = deepcopy(playlist)
        reference_items = sample(reference.items, k=(len(reference.items) // 2) + 1)
        reference.clear()
        reference.extend(reference_items)
        assert len(reference) >= 3

        other = [item for item in collection_merge_items]
        other.extend(reference[:2])  # both other and playlist have item 0, playlist does not have item 1
        other.extend(reference[3:])  # both other and playlist has items 3+

        playlist_items = [item for item in playlist if item not in reference]
        playlist.clear()
        playlist.extend(playlist_items)
        playlist.append(reference[0])  # both other and playlist have item 0
        playlist.extend(reference[2:])  # playlist has item 2, both other and playlist has items 3+
        playlist.append(next(item for item in other if item not in reference and item not in playlist))

        removed = [item for item in reference if item not in other or item not in playlist]
        assert len(removed) >= 2

        added = [item for item in other if item not in reference]
        added += [item for item in playlist if item not in reference and item not in added]
        assert added

        playlist.merge(other=other, reference=reference)
        assert all(item not in playlist for item in removed)
        assert all(item in playlist for item in added)
        assert len(playlist) == len(reference) - len(removed) + len(added)

    @staticmethod
    def test_merge_dunder_methods[T: Track](playlist: Playlist[T], collection_merge_items: Iterable[T]):
        initial_count = len(playlist)
        other = deepcopy(playlist)
        other.tracks.clear()
        other.tracks.extend(collection_merge_items)

        new_pl = playlist | other
        assert len(new_pl) == initial_count + len(other)
        assert new_pl[initial_count:] == other.items
        assert len(playlist) == initial_count

        playlist |= other
        assert len(playlist) == initial_count + len(other)
        assert playlist[initial_count:] == other.items


class LibraryTester(MusifyCollectionTester, ABC):
    """
    Run generic tests for :py:class:`Library` implementations.
    The collection must have 3 or more playlists and all playlists must be unique.
    """

    @abstractmethod
    def library(self, *args, **kwargs) -> Library:
        """Yields a loaded :py:class:`Library` object to be tested as pytest.fixture."""
        raise NotImplementedError

    @pytest.fixture
    def collection(self, library: Library) -> MusifyCollection:
        return library

    @staticmethod
    def assert_merge_playlists(source: Library, test_values: Any):
        """Run merge playlists function on ``source`` library against ``test_values`` and assert expected results"""
        # fine-grained merge functionality is tested in the playlist tester
        # we just need to assert the playlist was modified in some way
        test_library = deepcopy(source)
        test_library.merge_playlists(test_values)

        unchanged = next(iter(test_library.playlists.values()))
        assert len(source.playlists[unchanged.name]) == len(unchanged)

        for name, playlist in list(test_library.playlists.items())[1:]:
            assert len(source.playlists[name]) < len(playlist)

    @pytest.mark.slow
    def test_merge_playlists(self, library: Library, collection_merge_items: Iterable[MusifyItem]):
        merge_playlists = deepcopy(list(library.playlists.values())[:5])  # don't over test with too many playlists
        for playlist in merge_playlists[1:]:  # first playlist to remain unchanged
            playlist.extend(collection_merge_items)

        names = [pl.name for pl in merge_playlists]
        for name in list(library.playlists):
            if name not in names:
                library.playlists.pop(name)

        # Collection[Playlist]
        self.assert_merge_playlists(source=library, test_values=merge_playlists)

        # Mapping[str, Playlist]
        self.assert_merge_playlists(source=library, test_values={pl.name: pl for pl in merge_playlists})

        # Library
        test = deepcopy(library)
        test.playlists.clear()
        test.playlists.update({pl.name: pl for pl in merge_playlists})
        self.assert_merge_playlists(source=library, test_values=test)
