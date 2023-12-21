from typing import Any
from urllib.parse import parse_qs

import pytest

from syncify.remote.enums import RemoteObjectType as ObjectType
from syncify.spotify.api import SpotifyAPI
from tests.spotify.api.mock import SpotifyMock, idfn
from tests.utils import random_str


# TODO: add pretty_print_uris function test
class TestSpotifyAPICore:
    """Tester for core endpoints of :py:class:`SpotifyAPI`"""

    def test_get_self(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        assert api._user_data == {}
        assert api.get_self(update_user_data=False) == spotify_mock.user
        assert api._user_data == {}

        assert api.get_self(update_user_data=True) == spotify_mock.user
        assert api._user_data == spotify_mock.user

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
            spotify_mock: SpotifyMock
    ):
        # too small
        getattr(api, method_name)(limit=floor - 20, **kwargs)
        params = parse_qs(spotify_mock.last_request.query)
        assert "limit" in params
        assert int(params["limit"][0]) == floor

        # good value
        limit = floor + (ceil // 2)
        getattr(api, method_name)(limit=limit, **kwargs)
        params = parse_qs(spotify_mock.last_request.query)
        assert "limit" in params
        assert int(params["limit"][0]) == limit

        # too big
        getattr(api, method_name)(limit=ceil + 100, **kwargs)
        params = parse_qs(spotify_mock.last_request.query)
        assert "limit" in params
        assert int(params["limit"][0]) == ceil

    ###########################################################################
    ## /search endpoint functionality
    ###########################################################################
    def test_query_input_validation(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        assert api.query(query=None, kind=ObjectType.EPISODE) == []
        assert api.query(query="", kind=ObjectType.SHOW) == []
        # long queries that would cause the API to give an error should fail safely
        assert api.query(query=random_str(151, 200), kind=ObjectType.CHAPTER) == []
    
    @pytest.mark.parametrize("kind,query,limit", [
        (ObjectType.PLAYLIST, "super cool playlist", 5),
        (ObjectType.TRACK, "track title", 10),
        (ObjectType.ALBUM, "album title", 20),
    ], ids=idfn)
    def test_query(
            self,
            kind: ObjectType,
            query: str,
            limit: int,
            api: SpotifyAPI,
            spotify_mock: SpotifyMock,
    ):
        results = api.query(query=query, kind=kind, limit=limit)

        assert len(results) == min(len(spotify_mock.item_type_map[kind]), limit)
        for result in results:
            assert result["type"] == kind.name.casefold()

        request = spotify_mock.get_requests(url=f"{api.api_url_base}/search", params={"q": query})[0]
        params = parse_qs(request.query)

        assert params["q"][0] == query
        assert int(params["limit"][0]) == limit
        assert params["type"][0] == kind.name.casefold()
