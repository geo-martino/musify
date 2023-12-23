from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any

import pytest

from syncify.local.track import LocalTrack
from syncify.remote.library.collection import RemoteCollection, RemotePlaylist
from syncify.remote.library.item import RemoteItem, RemoteTrack
from tests.abstract.collection import ItemCollectionTester, PlaylistTester
from tests.local.utils import random_tracks
from tests.remote.utils import RemoteMock


class RemoteCollectionTester(ItemCollectionTester, metaclass=ABCMeta):

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[RemoteItem]:
        raise NotImplementedError

    @pytest.fixture(scope="module")
    def collection_merge_invalid(self, *args, **kwargs) -> Iterable[LocalTrack]:
        return random_tracks()

    def test_collection_getitem_dunder_method(
            self, collection: RemoteCollection, collection_merge_items: Iterable[RemoteItem]
    ):
        """:py:class:`ItemCollection` __getitem__ and __setitem__ tests"""
        item = collection.items[2]

        assert collection[1] == collection.items[1]
        assert collection[2] == collection.items[2]
        assert collection[:2] == collection.items[:2]

        assert collection[item] == item
        assert collection[item.name] == item
        assert collection[item.uri] == item
        assert collection[item.id] == item
        assert collection[item.url] == item
        assert collection[item.url_ext] == item

        invalid_item = next(item for item in collection_merge_items)
        with pytest.raises(KeyError):
            assert collection[invalid_item]
        with pytest.raises(KeyError):
            assert collection[invalid_item.name]
        with pytest.raises(KeyError):
            assert collection[invalid_item.uri]
        with pytest.raises(KeyError):
            assert collection[invalid_item.id]
        with pytest.raises(KeyError):
            assert collection[invalid_item.url]
        with pytest.raises(KeyError):
            assert collection[invalid_item.url_ext]

        with pytest.raises(KeyError):
            assert collection[item.remote_source]


class RemotePlaylistTester(RemoteCollectionTester, PlaylistTester, metaclass=ABCMeta):

    @abstractmethod
    def remote_mock(self, *args, **kwargs) -> RemoteMock:
        """Yields a requests_mock setup to return valid responses for the current remote source as a pytest.fixture"""
        raise NotImplementedError

    ###########################################################################
    ## Sync tests
    ###########################################################################

    @abstractmethod
    def sync_playlist(self, response_valid: dict[str, Any]) -> RemotePlaylist:
        """
        Yield a valid playlist that will produce idempotent results when reloaded from a :py:class:`RemoteMock`
        as a pytest.fixture
        """
        raise NotImplementedError

    @abstractmethod
    def sync_items(self, *args, **kwargs) -> list[RemoteTrack]:
        """
        Set API attribute on :py:class:`SpotifyPlaylist` and yield new items to sync to the playlist for sync tests
        as a pytest.fixture.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_sync_uris(url: str, remote_mock: RemoteMock) -> tuple[list[str], list[str]]:
        """Return tuple of lists of URIs added and URIs cleared when applying sync operations"""
        raise NotImplementedError

    @staticmethod
    def assert_playlist_loaded(sync_playlist: RemotePlaylist, remote_mock: RemoteMock, count: int = 1) -> None:
        """Assert the given playlist was fully reloaded through GET requests ``count`` number of times"""
        pages = remote_mock.calculate_pages_from_response(sync_playlist.response)

        requests = remote_mock.get_requests(url=sync_playlist.url, method="GET")
        requests += remote_mock.get_requests(url=sync_playlist.url + "/tracks", method="GET")

        assert len(requests) == pages * count

    @staticmethod
    def test_sync_dry_run(sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], remote_mock: RemoteMock):
        result_refresh_no_items = sync_playlist.sync(kind="refresh", reload=False)
        assert result_refresh_no_items.start == len(sync_playlist)
        assert result_refresh_no_items.added == result_refresh_no_items.start
        assert result_refresh_no_items.removed == result_refresh_no_items.start
        assert result_refresh_no_items.unchanged == 0
        assert result_refresh_no_items.difference == 0
        assert result_refresh_no_items.final == result_refresh_no_items.start
        assert len(remote_mock.request_history) == 0

        sync_items_extended = sync_items + sync_playlist[:10]
        result_refresh_with_items = sync_playlist.sync(items=sync_items_extended, kind="refresh", reload=True)
        assert result_refresh_with_items.start == len(sync_playlist)
        assert result_refresh_with_items.added == len(sync_items_extended)
        assert result_refresh_with_items.removed == result_refresh_with_items.start
        assert result_refresh_with_items.unchanged == 0
        assert result_refresh_with_items.difference == result_refresh_with_items.added - result_refresh_with_items.start
        assert result_refresh_with_items.final == result_refresh_with_items.added
        assert len(remote_mock.request_history) == 0  # reload does not happen on dry_run

        result_new = sync_playlist.sync(items=sync_items_extended, kind="new", reload=False)
        assert result_new.start == len(sync_playlist)
        assert result_new.added == len(sync_items)
        assert result_new.removed == 0
        assert result_new.unchanged == result_new.start
        assert result_new.difference == result_new.added
        assert result_new.final == result_new.start + result_new.difference
        assert len(remote_mock.request_history) == 0

        sync_uri = {track.uri for track in sync_items_extended}
        result_sync = sync_playlist.sync(items=sync_items_extended, kind="sync", reload=False)
        assert result_sync.start == len(sync_playlist)
        assert result_sync.added == len(sync_items)
        assert result_sync.removed == len([track.uri for track in sync_playlist if track.uri not in sync_uri])
        assert result_sync.unchanged == len([track.uri for track in sync_playlist if track.uri in sync_uri])
        assert result_sync.difference == len(sync_items) - result_sync.removed
        assert result_sync.final == result_sync.start + result_sync.difference
        assert len(remote_mock.request_history) == 0

    def test_sync_reload(self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], remote_mock: RemoteMock):
        start = len(sync_playlist)
        sync_playlist.tracks.clear()
        assert len(sync_playlist) == 0

        sync_playlist.sync(kind="sync", items=sync_items, reload=True, dry_run=False)
        # playlist will reload from mock so, for this test, it will just get back its original items
        assert len(sync_playlist) == start

        # 1 for skip dupes on add to playlist, 1 for reload
        self.assert_playlist_loaded(sync_playlist=sync_playlist, remote_mock=remote_mock, count=2)

    def test_sync_new(self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], remote_mock: RemoteMock):
        sync_items_extended = sync_items + sync_playlist.tracks[:5]
        result = sync_playlist.sync(kind="new", items=sync_items_extended, reload=False, dry_run=False)

        assert result.start == len(sync_playlist)
        assert result.added == len(sync_items)
        assert result.removed == 0
        assert result.unchanged == result.start
        assert result.difference == result.added
        assert result.final == result.start + result.difference

        uri_add, uri_clear = self.get_sync_uris(url=sync_playlist.url, remote_mock=remote_mock)
        assert uri_add == [track.uri for track in sync_items]
        assert uri_clear == []

        # 1 for skip dupes check on add to playlist
        self.assert_playlist_loaded(sync_playlist=sync_playlist, remote_mock=remote_mock, count=1)

    def test_sync_refresh(self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], remote_mock: RemoteMock):
        start = len(sync_playlist)
        result = sync_playlist.sync(items=sync_items, kind="refresh", reload=True, dry_run=False)

        assert result.start == start
        assert result.added == len(sync_items)
        assert result.removed == result.start
        assert result.unchanged == 0
        # assert result.difference == 0  # useless when mocking + reload
        # assert result.final == start  # useless when mocking + reload

        uri_add, uri_clear = self.get_sync_uris(url=sync_playlist.url, remote_mock=remote_mock)
        assert uri_add == [track.uri for track in sync_items]
        assert uri_clear == [track.uri for track in sync_playlist]

        # 1 load current tracks on remote when clearing, 1 for reload
        self.assert_playlist_loaded(sync_playlist=sync_playlist, remote_mock=remote_mock, count=2)

    def test_sync(self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], remote_mock: RemoteMock):
        sync_items_extended = sync_items + sync_playlist[:10]
        result = sync_playlist.sync(kind="sync", items=sync_items_extended, reload=False, dry_run=False)

        sync_uri = {track.uri for track in sync_items_extended}
        assert result.start == len(sync_playlist)
        assert result.added == len(sync_items)
        assert result.removed == len([track.uri for track in sync_playlist if track.uri not in sync_uri])
        assert result.unchanged == len([track.uri for track in sync_playlist if track.uri in sync_uri])
        assert result.difference == len(sync_items) - result.removed
        assert result.final == result.start + result.difference

        uri_add, uri_clear = self.get_sync_uris(url=sync_playlist.url, remote_mock=remote_mock)
        assert uri_add == [track.uri for track in sync_items]
        assert uri_clear == [track.uri for track in sync_playlist if track.uri not in sync_uri]

        # 1 load when clearing
        self.assert_playlist_loaded(sync_playlist=sync_playlist, remote_mock=remote_mock, count=1)
