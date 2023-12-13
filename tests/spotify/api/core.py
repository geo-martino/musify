from collections.abc import Callable
from functools import partial
from random import randrange
from typing import Any
from urllib.parse import urlparse, parse_qs

from requests_mock.mocker import Mocker
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember
from requests_mock.response import _Context as Context

from syncify.remote.enums import RemoteItemType
from syncify.spotify.api import SpotifyAPI
from tests.spotify.api.base_tester import SpotifyAPITesterHelpers
from tests.spotify.api.utils import SpotifyTestResponses as Responses
from tests.utils import random_str


class SpotifyAPICoreTester(SpotifyAPITesterHelpers):
    """Tester for core endpoints of :py:class:`SpotifyAPI`"""

    @staticmethod
    def test_get_self(api: SpotifyAPI, requests_mock: Mocker):
        url = f"{api.api_url_base}/me"
        expected = Responses.user()
        requests_mock.get(url=url, status_code=200, json=expected)

        assert api._user_data == {}
        assert api.get_self(update_user_data=False) == expected
        assert api._user_data == {}

        assert api.get_self(update_user_data=True) == expected
        assert api._user_data == expected

    @staticmethod
    def test_query_fails_safely(api: SpotifyAPI, requests_mock: Mocker):
        assert api.query(query=None, kind=RemoteItemType.EPISODE) == []
        assert api.query(query="", kind=RemoteItemType.SHOW) == []
        # long queries that would cause the API to give an error should fail safely
        assert api.query(query=random_str(151, 200), kind=RemoteItemType.CHAPTER) == []

        url = f"{api.api_url_base}/search"
        requests_mock.get(url=url, status_code=200, json={"error": "message"})
        assert api.query(query="valid query", kind=RemoteItemType.ARTIST, use_cache=False) == []

    def test_query_limits_limit(self, api: SpotifyAPI, requests_mock: Mocker):
        url = f"{api.api_url_base}/search"
        query = "valid query"
        kind = RemoteItemType.TRACK

        requests_mock.get(url=url, status_code=200, json={f"tracks": {"items": []}})
        self.limit_parameter_limited_test(
            test_function=partial(api.query, query=query, kind=kind, use_cache=False),
            requests_mock=requests_mock,
        )

    @staticmethod
    def assert_query_valid(
            api: SpotifyAPI,
            query: str,
            kind: RemoteItemType,
            limit: int,
            expected_getter: Callable[[Request], dict[str, Any]],
            requests_mock: Mocker
    ):
        """Run assertions for the results of a valid query on the Spotify API"""
        url = f"{api.api_url_base}/search"
        expected = {}

        def get_expected_json(req: Request, _: Context = None) -> dict[str, Any]:
            """Wrapper for expected response generator to retrieve the expected response"""
            nonlocal expected
            expected = expected_getter(req)
            return expected

        requests_mock.get(url=url, status_code=200, json=get_expected_json)
        response = api.query(query=query, kind=kind, limit=limit, use_cache=False)

        assert response == expected[f"{kind.name.casefold()}s"]["items"]
        assert expected[f"{kind.name.casefold()}s"]["limit"] == limit
        assert expected[f"{kind.name.casefold()}s"]["total"] >= limit
        assert len(response) <= expected[f"{kind.name.casefold()}s"]["total"]

        request = requests_mock.last_request
        params = parse_qs(urlparse(request.url).query)
        assert params["q"][0] == query
        assert int(params["limit"][0]) == limit
        assert params["type"][0] == kind.name.casefold()

    def test_query_track(self, api: SpotifyAPI, requests_mock: Mocker):
        limit = 10
        kind = RemoteItemType.TRACK

        def get_expected_json(request: Request) -> dict[str, Any]:
            """Dynamically generate expected response"""
            total = limit + randrange(0, 50)
            items = [Responses.track(album=True, artists=True) for _ in range(total)]
            items_block = Responses.format_items_block(url_base=request.url, items=items, limit=limit)
            return {f"tracks": items_block}

        self.assert_query_valid(
            api=api,
            query="track title",
            kind=kind,
            limit=limit,
            expected_getter=get_expected_json,
            requests_mock=requests_mock
        )

    def test_query_album(self, api: SpotifyAPI, requests_mock: Mocker):
        limit = 20
        kind = RemoteItemType.ALBUM

        def get_expected_json(request: Request) -> dict[str, Any]:
            """Dynamically generate expected response"""
            total = limit + randrange(0, 50)
            items = [Responses.album(extend=False, artists=True, tracks=False) for _ in range(total)]
            items_block = Responses.format_items_block(url_base=request.url, items=items, limit=limit)
            return {f"albums": items_block}

        self.assert_query_valid(
            api=api,
            query="album title",
            kind=kind,
            limit=limit,
            expected_getter=get_expected_json,
            requests_mock=requests_mock
        )
