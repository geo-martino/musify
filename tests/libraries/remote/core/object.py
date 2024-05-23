from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any

import pytest
from aioresponses.core import RequestCall

from musify.exception import MusifyKeyError
from musify.libraries.local.track import LocalTrack
from musify.libraries.remote.core.api import RemoteAPI
from musify.libraries.remote.core.base import RemoteItem
from musify.libraries.remote.core.object import RemoteTrack, RemoteCollection, RemotePlaylist
from tests.libraries.core.collection import MusifyCollectionTester, PlaylistTester
from tests.libraries.local.track.utils import random_tracks
from tests.libraries.remote.core.utils import RemoteMock


class RemoteCollectionTester(MusifyCollectionTester, metaclass=ABCMeta):

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[RemoteItem]:
        raise NotImplementedError

    @pytest.fixture(scope="module")
    def collection_merge_invalid(self, *_, **__) -> Iterable[LocalTrack]:
        return random_tracks()

    def test_collection_getitem_dunder_method(
            self, collection: RemoteCollection, collection_merge_items: Iterable[RemoteItem]
    ):
        """:py:class:`MusifyCollection` __getitem__ and __setitem__ tests"""
        idx, item = next((i, item) for i, item in enumerate(collection.items) if collection.items.count(item) == 1)

        assert collection[1] == collection.items[1]
        assert collection[:2] == collection.items[:2]
        assert collection[idx] == collection.items[idx] == item

        assert collection[item] == item
        assert collection[item.name] == item
        assert collection[item.uri] == item
        assert collection[item.id] == item
        assert collection[item.url] == item
        assert collection[item.url_ext] == item

        invalid_item = next(item for item in collection_merge_items)
        with pytest.raises(MusifyKeyError):
            assert collection[invalid_item]
        with pytest.raises(MusifyKeyError):
            assert collection[invalid_item.name]
        with pytest.raises(MusifyKeyError):
            assert collection[invalid_item.uri]
        with pytest.raises(MusifyKeyError):
            assert collection[invalid_item.id]
        with pytest.raises(MusifyKeyError):
            assert collection[invalid_item.url]
        with pytest.raises(MusifyKeyError):
            assert collection[invalid_item.url_ext]

        with pytest.raises(MusifyKeyError):
            assert collection["this key does not exist"]


class RemotePlaylistTester(RemoteCollectionTester, PlaylistTester, metaclass=ABCMeta):

    @staticmethod
    def _get_payload_from_request(request: RequestCall) -> dict[str, Any] | None:
        return request.kwargs.get("body", request.kwargs.get("json"))

    ###########################################################################
    ## Sync tests
    ###########################################################################
    @abstractmethod
    def sync_playlist(self, response_valid: dict[str, Any], api: RemoteAPI) -> RemotePlaylist:
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
    async def get_sync_uris(url: str, api_mock: RemoteMock) -> tuple[list[str], list[str]]:
        """Return tuple of lists of URIs added and URIs cleared when applying sync operations"""
        raise NotImplementedError

    @staticmethod
    async def assert_playlist_loaded(sync_playlist: RemotePlaylist, api_mock: RemoteMock, count: int = 1) -> None:
        """Assert the given playlist was fully reloaded through GET requests ``count`` number of times"""
        pages = api_mock.calculate_pages_from_response(sync_playlist.response)

        requests = await api_mock.get_requests(method="GET", url=sync_playlist.url)
        requests += await api_mock.get_requests(method="GET", url=sync_playlist.url + "/tracks")

        assert len(requests) == pages * count

    @staticmethod
    async def test_sync_dry_run(sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], api_mock: RemoteMock):
        result_refresh_no_items = await sync_playlist.sync(kind="refresh", reload=False)
        assert result_refresh_no_items.start == len(sync_playlist)
        assert result_refresh_no_items.added == result_refresh_no_items.start
        assert result_refresh_no_items.removed == result_refresh_no_items.start
        assert result_refresh_no_items.unchanged == 0
        assert result_refresh_no_items.difference == 0
        assert result_refresh_no_items.final == result_refresh_no_items.start
        api_mock.assert_not_called()

        sync_items_extended = sync_items + sync_playlist[:10]
        result_refresh_with_items = await sync_playlist.sync(items=sync_items_extended, kind="refresh", reload=True)
        assert result_refresh_with_items.start == len(sync_playlist)
        assert result_refresh_with_items.added == len(sync_items_extended)
        assert result_refresh_with_items.removed == result_refresh_with_items.start
        assert result_refresh_with_items.unchanged == 0
        assert result_refresh_with_items.difference == result_refresh_with_items.added - result_refresh_with_items.start
        assert result_refresh_with_items.final == result_refresh_with_items.added
        api_mock.assert_not_called()  # reload does not happen on dry_run

        result_new = await sync_playlist.sync(items=sync_items_extended, kind="new", reload=False)
        assert result_new.start == len(sync_playlist)
        assert result_new.added == len(sync_items)
        assert result_new.removed == 0
        assert result_new.unchanged == result_new.start
        assert result_new.difference == result_new.added
        assert result_new.final == result_new.start + result_new.difference
        api_mock.assert_not_called()

        sync_uri = {track.uri for track in sync_items_extended}
        result_sync = await sync_playlist.sync(items=sync_items_extended, kind="sync", reload=False)
        assert result_sync.start == len(sync_playlist)
        assert result_sync.added == len(sync_items)
        assert result_sync.removed == len([track.uri for track in sync_playlist if track.uri not in sync_uri])
        assert result_sync.unchanged == len([track.uri for track in sync_playlist if track.uri in sync_uri])
        assert result_sync.difference == len(sync_items) - result_sync.removed
        assert result_sync.final == result_sync.start + result_sync.difference
        api_mock.assert_not_called()

    async def test_sync_reload(
            self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], api_mock: RemoteMock
    ):
        start = len(sync_playlist)
        sync_playlist.tracks.clear()
        assert len(sync_playlist) == 0

        await sync_playlist.sync(kind="sync", items=sync_items, reload=True, dry_run=False)
        # playlist will reload from mock so, for this test, it will just get back its original items
        assert len(sync_playlist) == start

        # 1 for skip dupes on add to playlist, 1 for reload
        await self.assert_playlist_loaded(sync_playlist=sync_playlist, api_mock=api_mock, count=2)

    async def test_sync_new(self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], api_mock: RemoteMock):
        sync_items_extended = sync_items + sync_playlist.tracks[:5]
        result = await sync_playlist.sync(kind="new", items=sync_items_extended, reload=False, dry_run=False)

        assert result.start == len(sync_playlist)
        assert result.added == len(sync_items)
        assert result.removed == 0
        assert result.unchanged == result.start
        assert result.difference == result.added
        assert result.final == result.start + result.difference

        uri_add, uri_clear = await self.get_sync_uris(url=sync_playlist.url, api_mock=api_mock)
        assert uri_add == [track.uri for track in sync_items]
        assert uri_clear == []

        # 1 for skip dupes check on add to playlist
        await self.assert_playlist_loaded(sync_playlist=sync_playlist, api_mock=api_mock, count=1)

    async def test_sync_refresh(
            self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], api_mock: RemoteMock
    ):
        start = len(sync_playlist)
        result = await sync_playlist.sync(items=sync_items, kind="refresh", reload=True, dry_run=False)

        assert result.start == start
        assert result.added == len(sync_items)
        assert result.removed == result.start
        assert result.unchanged == 0
        # assert result.difference == 0  # useless when mocking + reload
        # assert result.final == start  # useless when mocking + reload

        uri_add, uri_clear = await self.get_sync_uris(url=sync_playlist.url, api_mock=api_mock)
        assert uri_add == [track.uri for track in sync_items]
        assert uri_clear == [track.uri for track in sync_playlist]

        # 1 load current tracks on remote when clearing, 1 for reload
        await self.assert_playlist_loaded(sync_playlist=sync_playlist, api_mock=api_mock, count=2)

    async def test_sync(self, sync_playlist: RemotePlaylist, sync_items: list[RemoteTrack], api_mock: RemoteMock):
        sync_items_extended = sync_items + sync_playlist[:10]
        result = await sync_playlist.sync(kind="sync", items=sync_items_extended, reload=False, dry_run=False)

        sync_uri = {track.uri for track in sync_items_extended}
        assert result.start == len(sync_playlist)
        assert result.added == len(sync_items)
        assert result.removed == len([track.uri for track in sync_playlist if track.uri not in sync_uri])
        assert result.unchanged == len([track.uri for track in sync_playlist if track.uri in sync_uri])
        assert result.difference == len(sync_items) - result.removed
        assert result.final == result.start + result.difference

        uri_add, uri_clear = await self.get_sync_uris(url=sync_playlist.url, api_mock=api_mock)
        assert uri_add == [track.uri for track in sync_items]
        assert uri_clear == [track.uri for track in sync_playlist if track.uri not in sync_uri]

        # 1 load when clearing
        await self.assert_playlist_loaded(sync_playlist=sync_playlist, api_mock=api_mock, count=1)
