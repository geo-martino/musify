from copy import deepcopy
from typing import Any
from urllib.parse import parse_qs

import pytest

from syncify.remote.enums import RemoteObjectType as ObjectType
from syncify.spotify import URL_EXT
from syncify.spotify.api import SpotifyAPI
from tests.spotify.api.mock import SpotifyMock, idfn
from tests.utils import random_str, get_stdout


class TestSpotifyAPICore:
    """Tester for core endpoints of :py:class:`SpotifyAPI`"""

    @pytest.mark.parametrize("method_name,kwargs,floor,ceil", [
        ("query", {"query": "valid query", "kind": ObjectType.TRACK}, 1, 50),
        ("get_user_items", {"kind": ObjectType.PLAYLIST}, 1, 50)
    ], ids=idfn)
    def test_limit_param_limited(
            self,
            method_name: str,
            kwargs: dict[str, Any],
            floor: int,
            ceil: int,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        # too small
        getattr(api, method_name)(limit=floor - 20, **kwargs)
        params = parse_qs(api_mock.last_request.query)
        assert "limit" in params
        assert int(params["limit"][0]) == floor

        # good value
        limit = floor + (ceil // 2)
        getattr(api, method_name)(limit=limit, **kwargs)
        params = parse_qs(api_mock.last_request.query)
        assert "limit" in params
        assert int(params["limit"][0]) == limit

        # too big
        getattr(api, method_name)(limit=ceil + 100, **kwargs)
        params = parse_qs(api_mock.last_request.query)
        assert "limit" in params
        assert int(params["limit"][0]) == ceil

    ###########################################################################
    ## /me + /search endpoints
    ###########################################################################
    def test_get_self(self, api: SpotifyAPI, api_mock: SpotifyMock):
        api._user_data = {}
        assert api.get_self(update_user_data=False) == api_mock.user
        assert api._user_data == {}

        assert api.get_self(update_user_data=True) == api_mock.user
        assert api._user_data == api_mock.user

    def test_query_input_validation(self, api: SpotifyAPI, api_mock: SpotifyMock):
        assert api.query(query=None, kind=ObjectType.EPISODE) == []
        assert api.query(query="", kind=ObjectType.SHOW) == []
        # long queries that would cause the API to give an error should fail safely
        assert api.query(query=random_str(151, 200), kind=ObjectType.CHAPTER) == []

    # TODO: expand mock to allow testing for all RemoteObjectTypes
    @pytest.mark.parametrize("kind,query,limit", [
        (ObjectType.PLAYLIST, "super cool playlist", 5),
        (ObjectType.TRACK, "track 2", 10),
        (ObjectType.ALBUM, "best album title", 20),
        (ObjectType.ARTIST, "really cool artist name", 20),
        # (ObjectType.SHOW, "amazing show", 20),
        # (ObjectType.EPISODE, "incredible episode", 20),
        # (ObjectType.AUDIOBOOK, "i love this audiobook", 20),
    ], ids=idfn)
    def test_query(
            self,
            kind: ObjectType,
            query: str,
            limit: int,
            api: SpotifyAPI,
            api_mock: SpotifyMock,
    ):
        expected = api_mock.item_type_map[kind]
        results = api.query(query=query, kind=kind, limit=limit)

        assert len(results) <= min(len(expected), limit)
        for result in results:
            assert result["type"] == kind.name.casefold()

        request = api_mock.get_requests(url=f"{api.api_url_base}/search", params={"q": query})[0]
        params = parse_qs(request.query)

        assert params["q"][0] == query
        assert int(params["limit"][0]) == limit
        assert params["type"][0] == kind.name.casefold()

    ###########################################################################
    ## Utilities
    ###########################################################################
    # TODO: expand mock to allow testing for all extendable RemoteObjectTypes
    @pytest.mark.parametrize("kind", [
        ObjectType.PLAYLIST, ObjectType.ALBUM,  # ObjectType.SHOW, ObjectType.AUDIOBOOK,
    ], ids=idfn)
    def test_pretty_print_uris(
            self, kind: ObjectType, api: SpotifyAPI, api_mock: SpotifyMock, capfd: pytest.CaptureFixture
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        key = api.collection_item_map.get(kind, kind).name.casefold() + "s"
        source = deepcopy(next(item for item in api_mock.item_type_map[kind] if item[key]["total"] > 50))

        api.print_collection(value=source)
        stdout = get_stdout(capfd)

        # printed in blocks
        blocks = [block for block in stdout.strip().split("\n\n") if URL_EXT in block]
        assert len(blocks) == len(api_mock.request_history)

        # lines printed = total tracks + 1 extra for title
        lines = [line for line in stdout.strip().split("\n") if URL_EXT in line]
        assert len(lines) == source[key]["total"] + 1
