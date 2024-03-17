from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any
from urllib.parse import parse_qs

from musify.shared.remote.enum import RemoteObjectType
from musify.spotify.api import SpotifyAPI
from musify.spotify.base import SpotifyItem
from musify.spotify.object import SpotifyCollectionLoader, SpotifyTrack
from tests.shared.remote.object import RemoteCollectionTester
from tests.spotify.api.mock import SpotifyMock


class SpotifyCollectionLoaderTester(RemoteCollectionTester, metaclass=ABCMeta):

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[SpotifyItem]:
        raise NotImplementedError

    @staticmethod
    def test_load_without_items(
            collection: SpotifyCollectionLoader,
            response_valid: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        unit = collection.__class__.__name__.removeprefix("Spotify")
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.lower() + "s"

        test = collection.__class__.load(response_valid["href"], api=api, extend_tracks=True)

        assert test.name == response_valid["name"]
        assert test.id == response_valid["id"]
        assert test.url == response_valid["href"]

        requests = api_mock.get_requests(test.url)
        requests += api_mock.get_requests(f"{test.url}/{key}")
        requests += api_mock.get_requests(f"{collection.api.url}/audio-features")

        # 1 call for initial collection + (pages - 1) for tracks + (pages) for audio-features
        assert len(requests) == 2 * api_mock.calculate_pages_from_response(test.response)

        # input items given, but no key to search on still loads
        test = collection.__class__.load(response_valid, api=api, items=response_valid.pop(key), extend_tracks=True)

        assert test.name == response_valid["name"]
        assert test.id == response_valid["id"]
        assert test.url == response_valid["href"]

    @staticmethod
    def assert_load_with_tracks(
            cls: type[SpotifyCollectionLoader],
            items: list[SpotifyTrack],
            response: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
    ):
        """Run test with assertions on load method with given ``items``"""
        unit = cls.__name__.removeprefix("Spotify")
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.lower() + "s"

        test = cls.load(response, api=api, items=items, extend_tracks=True)
        assert len(test.response[key]["items"]) == response[key]["total"]
        assert len(test.items) == response[key]["total"]
        assert not api_mock.get_requests(test.url)  # playlist URL was not called

        # requests to extend album start from page 2 onward
        requests = api_mock.get_requests(test.url)
        requests += api_mock.get_requests(f"{test.url}/{key}")
        requests += api_mock.get_requests(f"{api.url}/audio-features")

        # 0 calls for initial collection + (extend_pages - 1) for tracks + (extend_pages) for audio-features
        # + (get_pages) for audio-features get on response items not in input items
        if kind == RemoteObjectType.PLAYLIST:
            input_ids = {item["track"]["id"] for item in response["tracks"]["items"]} - {item.id for item in items}
        else:
            input_ids = {item["id"] for item in response["tracks"]["items"]} - {item.id for item in items}
        get_pages = api_mock.calculate_pages(limit=test.response[key]["limit"], total=len(input_ids))
        extend_pages = api_mock.calculate_pages_from_response(test.response)
        assert len(requests) == 2 * extend_pages - 1 + get_pages

        # ensure none of the items ids were requested
        input_ids = {item.id for item in items}
        for request in api_mock.get_requests(f"{test.url}/{key}"):
            params = parse_qs(request.query)
            if "ids" not in params:
                continue

            assert not input_ids.intersection(params["ids"][0].split(","))
