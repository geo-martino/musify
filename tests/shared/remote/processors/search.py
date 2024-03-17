from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable
from copy import copy
from urllib.parse import parse_qs

import pytest

from musify.local.collection import LocalAlbum
from musify.local.track import LocalTrack
from musify.shared.core.base import MusifyItem
from musify.shared.core.collection import MusifyCollection
from musify.shared.core.enum import TagFields as Tag
from musify.shared.core.object import BasicCollection, Album
from musify.shared.remote.enum import RemoteObjectType
from musify.shared.remote.processors.search import RemoteItemSearcher, SearchSettings
from tests.local.track.utils import random_track, random_tracks
from tests.shared.core.misc import PrettyPrinterTester
from tests.shared.remote.utils import RemoteMock


class RemoteItemSearcherTester(PrettyPrinterTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`RemoteItemSearcher` implementations."""

    @pytest.fixture
    def obj(self, searcher: RemoteItemSearcher) -> RemoteItemSearcher:
        return searcher

    @abstractmethod
    def searcher(self, *args, **kwargs) -> RemoteItemSearcher:
        """Yields a valid :py:class:`RemoteItemSearcher` for the current remote source as a pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def search_items(self, *args, **kwargs) -> list[LocalTrack]:
        """
        Yields a list of :py:class:`LocalTrack` that should be returned from the query endpoint when querying items.
        Each item must have a ``remote_wrangler`` associated with it.
        Mark as a pytest.fixture.
        """
        raise NotImplementedError

    @abstractmethod
    def search_albums(self, *args, **kwargs) -> list[LocalAlbum]:
        """
        Yields a list of :py:class:`LocalAlbum` that should be returned from the query endpoint when querying items.
        Each item must have a ``remote_wrangler`` associated with it.
        Mark as a pytest.fixture.
        """
        raise NotImplementedError

    # noinspection PyProtectedMember
    @pytest.fixture
    def unmatchable_items(self) -> list[LocalTrack]:
        """
        Yields a list of :py:class:`LocalTrack` that returns no matchable results when querying items.
        Mark as a pytest.fixture
        """
        unmatchable_items = random_tracks(5)
        for item in unmatchable_items:
            item.uri = None
            assert item.has_uri is None

            item.title = item.artist = item.album = None
            item._reader.file.info.length = -3000
            item.year = 1000

        return unmatchable_items

    @staticmethod
    def test_get_results(searcher: RemoteItemSearcher, api_mock: RemoteMock):
        api_mock.reset_mock()  # test checks the number of requests made

        settings = SearchSettings(
            search_fields_1=[Tag.NAME, Tag.ARTIST],  # query mock always returns match on name
            search_fields_2=[Tag.NAME, Tag.ALBUM],
            search_fields_3=[Tag.NAME, Tag.YEAR],
            match_fields={Tag.TITLE},
            result_count=7
        )
        item = random_track()
        results = searcher._get_results(item=item, kind=RemoteObjectType.TRACK, settings=settings)
        requests = api_mock.get_requests(method="GET")
        assert len(results) == settings.result_count
        assert len(requests) == 1

        expected = [str(item.clean_tags.get(key)) for key in settings.search_fields_1]
        found = False
        for k, v in parse_qs(requests[0].query).items():
            if expected == v[0].split():
                found = True
                break

        if not found:
            raise AssertionError("Query string not found")

        # make these tags too long to query forcing them to return on results
        item.artist = 'b' * 200
        item.album = 'c' * 200
        api_mock.reset_mock()  # test checks the number of requests made

        results = searcher._get_results(item=item, kind=RemoteObjectType.TRACK, settings=settings)
        requests = api_mock.get_requests(method="GET")
        assert len(results) == settings.result_count
        assert len(requests) == 1

        expected = [str(item.clean_tags.get(key)) for key in settings.search_fields_3]
        found = False
        for k, v in parse_qs(requests[0].query).items():
            if expected == v[0].split():
                found = True
                break

        if not found:
            raise AssertionError("Query string not found")

    ###########################################################################
    ## _search_<object type> tests
    ###########################################################################
    @staticmethod
    def assert_search(
            search_function: Callable[[Iterable[MusifyItem] | MusifyCollection], None],
            collection: Iterable[MusifyItem],
            search_items: Iterable[MusifyItem],
            unmatchable_items: Iterable[MusifyItem],
    ):
        """Run search on given ``collection`` type against the ``search_function`` and assert the results"""
        for item in collection:
            assert item.has_uri is None
            assert item.uri is None

        search_function(collection)
        for item in search_items:
            assert item.has_uri
            assert item.uri is not None
        for item in unmatchable_items:
            assert item.has_uri is None
            assert item.uri is None

        # test search does not replace URIs
        assert len({item.uri for item in collection}) > 1  # currently more than 1 unique URI in collection
        uri = next(item for item in collection).uri
        for item in search_items:
            item.uri = uri

        search_function(collection)
        for item in search_items:
            assert item.has_uri
            assert item.uri == uri
        for item in unmatchable_items:
            assert item.has_uri is None
            assert item.uri is None

    def test_search_items(
            self, searcher: RemoteItemSearcher, search_items: list[MusifyItem], unmatchable_items: list[LocalTrack]
    ):
        self.assert_search(
            searcher._search_items,
            collection=BasicCollection(name="test", items=search_items + unmatchable_items),
            search_items=search_items,
            unmatchable_items=unmatchable_items
        )

    def test_search_album(
            self, searcher: RemoteItemSearcher, search_albums: list[Album], unmatchable_items: list[LocalTrack]
    ):
        collection = search_albums[0]
        search_items = copy(collection.tracks)
        collection.tracks.extend(unmatchable_items)

        self.assert_search(
            searcher._search_album,
            collection=collection,
            search_items=search_items,
            unmatchable_items=unmatchable_items
        )

    ###########################################################################
    ## _search_collection tests
    ###########################################################################
    @staticmethod
    @pytest.fixture
    def search_album(search_albums: list[LocalAlbum]):
        """Process and prepare a single album for searching"""
        collection = next(album for album in search_albums if 2 < len(album) == len(set(album.tracks)))
        assert not collection.compilation  # this forces an album search

        skip = 0
        for skip, item in enumerate(collection[:len(collection) // 2], 1):
            item.uri = item.remote_wrangler.unavailable_uri_dummy
            assert item.has_uri is False
        assert skip > 0  # check test input is valid

        return collection

    @staticmethod
    def test_search_result_items(
            searcher: RemoteItemSearcher, search_items: list[LocalTrack], unmatchable_items: list[LocalTrack]
    ):
        collection = BasicCollection(name="test", items=search_items + unmatchable_items)

        result = searcher._search_collection(collection)
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(collection)
        assert len(result.matched) == len(search_items)
        assert len(result.unmatched) == len(unmatchable_items)
        assert len(result.skipped) == 0

        # skips all matched on 2nd run
        result = searcher._search_collection(collection)
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(collection)
        assert len(result.matched) == 0
        assert len(result.unmatched) == len(unmatchable_items)
        assert len(result.skipped) == len(search_items)

    @staticmethod
    def test_search_result_album(searcher: RemoteItemSearcher, search_album: LocalAlbum):
        skip = len([item for item in search_album if item.has_uri is not None])

        result = searcher._search_collection(search_album)
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(search_album)
        assert len(result.matched) == len(search_album) - skip
        assert len(result.unmatched) == 0
        assert len(result.skipped) == skip

        # skips all matched on 2nd run
        result = searcher._search_collection(search_album)
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(search_album)
        assert len(result.matched) == 0
        assert len(result.unmatched) == 0
        assert len(result.skipped) == len(search_album)

    @staticmethod
    def test_search_result_combined(
            searcher: RemoteItemSearcher,
            search_items: list[LocalTrack],
            search_album: LocalAlbum,
            unmatchable_items: list[LocalTrack],
    ):
        matchable = len(search_album) + len(search_items)
        search_album.items.extend(search_items)
        search_album.items.extend(unmatchable_items)
        skip = len([item for item in search_album if item.has_uri is not None])

        result = searcher._search_collection(search_album)
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(search_album)

        assert len(result.matched) == matchable - skip
        assert len(result.unmatched) == len(unmatchable_items)
        assert len(result.skipped) == skip

        # skips all matched on 2nd run
        result = searcher._search_collection(search_album)
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(search_album)
        assert len(result.matched) == 0
        assert len(result.unmatched) == len(unmatchable_items)
        assert len(result.skipped) == matchable

    ###########################################################################
    ## main search tests
    ###########################################################################
    @staticmethod
    def test_search(
            searcher: RemoteItemSearcher,
            search_items: list[LocalTrack],
            search_album: LocalAlbum,
            unmatchable_items: list[LocalTrack],
            api_mock: RemoteMock,
    ):
        search_collection = BasicCollection(name="test", items=search_items + unmatchable_items)
        skip_album = len([item for item in search_album if item.has_uri is not None])

        results = searcher([search_collection, search_album])

        result = results[search_collection.name]
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(search_collection)
        assert len(result.matched) == len(search_items)
        assert len(result.unmatched) == len(unmatchable_items)
        assert len(result.skipped) == 0

        result = results[search_album.name]
        assert len(result.matched) + len(result.unmatched) + len(result.skipped) == len(search_album)
        assert len(result.matched) == len(search_album) - skip_album
        assert len(result.unmatched) == 0
        assert len(result.skipped) == skip_album

        # check nothing happens on matched collections
        api_mock.reset_mock()  # test checks the number of requests made
        search_matched = BasicCollection(name="test", items=search_items)
        assert len(searcher.search([search_matched, search_album])) == 0
        assert len(api_mock.request_history) == 0
