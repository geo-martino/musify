from abc import ABCMeta
from collections.abc import Iterable, Collection
from random import randrange, sample

import pytest

from tests.local.track.utils import random_tracks
from syncify.local.collection import LocalCollection
from syncify.local.track import LocalTrack
from syncify.shared.exception import SyncifyKeyError
from syncify.spotify.object import SpotifyTrack
from tests.shared.core.collection import ItemCollectionTester
from tests.spotify.api.mock import SpotifyMock


class LocalCollectionTester(ItemCollectionTester, metaclass=ABCMeta):

    @pytest.fixture
    def collection_merge_items(self) -> Iterable[LocalTrack]:
        return random_tracks(randrange(5, 10))

    @pytest.fixture(scope="module")
    def collection_merge_invalid(self, spotify_mock: SpotifyMock) -> Collection[SpotifyTrack]:
        return tuple(SpotifyTrack(response) for response in sample(spotify_mock.tracks, k=5))

    def test_collection_getitem_dunder_method(
            self, collection: LocalCollection, collection_merge_items: Iterable[LocalTrack]
    ):
        """:py:class:`ItemCollection` __getitem__ and __setitem__ tests"""
        idx, item = next((i, item) for i, item in enumerate(collection.items) if collection.items.count(item) == 1)

        assert collection[1] == collection.items[1]
        assert collection[:2] == collection.items[:2]
        assert collection[idx] == collection.items[idx] == item

        assert collection[item] == item
        assert collection[item.name] == item
        assert collection[item.path] == item

        if collection.remote_wrangler is not None:
            assert collection[item.uri] == item
        else:
            with pytest.raises(SyncifyKeyError):
                assert collection[item.uri]

        invalid_track = next(item for item in collection_merge_items)
        with pytest.raises(SyncifyKeyError):
            assert collection[invalid_track]
        with pytest.raises(SyncifyKeyError):
            assert collection[invalid_track.name]
        with pytest.raises(SyncifyKeyError):
            assert collection[invalid_track.path]
        with pytest.raises(SyncifyKeyError):
            assert collection[invalid_track.uri]

    @staticmethod
    def test_merge_tracks(collection: LocalCollection, collection_merge_items: Collection[SpotifyTrack]):
        length = len(collection.items)
        assert all(item not in collection.items for item in collection_merge_items)

        collection.merge_tracks(collection_merge_items)
        assert len(collection.items) == length
