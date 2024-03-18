from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any
from urllib.parse import parse_qs

import pytest

from musify.shared.remote.enum import RemoteObjectType
from musify.spotify.api import SpotifyAPI
from musify.spotify.base import SpotifyItem, SpotifyObject
from musify.spotify.object import SpotifyCollectionLoader, SpotifyArtist
from tests.shared.remote.object import RemoteCollectionTester
from tests.spotify.api.mock import SpotifyMock


class SpotifyCollectionLoaderTester(RemoteCollectionTester, metaclass=ABCMeta):

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[SpotifyItem]:
        raise NotImplementedError

    @abstractmethod
    def item_kind(self, api: SpotifyAPI) -> RemoteObjectType:
        """Yields the RemoteObjectType of items in this collection as a pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def item_key(self, item_kind: RemoteObjectType) -> str:
        """Yields the key of items in this collection as a pytest.fixture"""
        return item_kind.name.lower() + "s"

    ###########################################################################
    ## Assertions
    ###########################################################################
    @staticmethod
    def assert_load_with_items_requests[T: SpotifyObject](
            response: dict[str, Any],
            result: SpotifyCollectionLoader[T],
            items: list[T],
            key: str,
            api_mock: SpotifyMock,
    ):
        """Run assertions on the requests from load method with given ``items``"""
        assert len(result.response[key][result.api.items_key]) == response[key]["total"]
        assert len(result.items) == response[key]["total"]
        assert not api_mock.get_requests(result.url)  # main collection URL was not called

        # ensure none of the input_ids were requested
        input_ids = {item.id for item in items}
        for request in api_mock.get_requests(f"{result.url}/{key}"):
            params = parse_qs(request.query)
            if "ids" not in params:
                continue

            assert not input_ids.intersection(params["ids"][0].split(","))

    @staticmethod
    def assert_load_with_items_extended[T: SpotifyObject](
            response: dict[str, Any],
            result: SpotifyCollectionLoader[T],
            items: list[T],
            kind: RemoteObjectType,
            key: str,
            api_mock: SpotifyMock,
    ):
        """Run assertions on the requests for missing data from load method with given ``items``"""
        requests_missing = api_mock.get_requests(f"{result.api.url}/{key}")
        limit = response[key]["limit"]
        input_ids = {item.id for item in items}
        response_item_ids = {
            item[key.rstrip("s")]["id"] if kind == RemoteObjectType.PLAYLIST else item["id"]
            for item in response[key][result.api.items_key]
        }
        assert len(requests_missing) == api_mock.calculate_pages(limit=limit, total=len(response_item_ids - input_ids))

    ###########################################################################
    ## Tests
    ###########################################################################
    @staticmethod
    @abstractmethod
    def get_load_without_items(
            loader: SpotifyCollectionLoader,
            response_valid: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        """Yields the results from 'load' where no items are given as a pytest.fixture"""
        raise NotImplementedError

    def test_load_without_items(
            self,
            collection: SpotifyCollectionLoader,
            response_valid: dict[str, Any],
            item_key: str,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        result = self.get_load_without_items(
            loader=collection, response_valid=response_valid, api=api, api_mock=api_mock
        )

        assert result.name == response_valid["name"]
        assert result.id == response_valid["id"]
        assert result.url == response_valid["href"]

        expected = api_mock.calculate_pages_from_response(result.response, item_key=item_key)
        if not isinstance(result, SpotifyArtist):
            expected -= 1  # -1 for not calling initial page

        assert len(api_mock.get_requests(result.url)) == 1
        assert len(api_mock.get_requests(f"{result.url}/{item_key}")) == expected
        assert not api_mock.get_requests(f"{api.url}/audio-features")
        assert not api_mock.get_requests(f"{api.url}/audio-analysis")

        # input items given, but no key to search on still loads
        result = collection.load(response_valid, api=api, items=response_valid.pop(item_key), extend_tracks=True)

        assert result.name == response_valid["name"]
        assert result.id == response_valid["id"]
        assert result.url == response_valid["href"]
