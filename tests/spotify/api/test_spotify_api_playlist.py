from copy import deepcopy
from random import randrange, sample
from typing import Any

import pytest

from musify import PROGRAM_NAME
from musify.shared.remote.enum import RemoteObjectType as ObjectType, RemoteIDType
from musify.shared.remote.exception import RemoteObjectTypeError, RemoteIDTypeError
from musify.spotify.api import SpotifyAPI
from tests.shared.remote.utils import ALL_ITEM_TYPES
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.utils import random_ids, random_id, random_id_type, random_id_types
from tests.spotify.utils import random_uris, random_api_urls, random_ext_urls


class TestSpotifyAPIPlaylists:
    """Tester for playlist modification type endpoints of :py:class:`SpotifyAPI`"""

    @staticmethod
    @pytest.fixture
    def playlist(api_mock: SpotifyMock) -> dict[str, Any]:
        """Yields a response representing a user playlist on Spotify"""
        return next(deepcopy(pl) for pl in api_mock.user_playlists if pl["tracks"]["total"] > api_mock.limit_lower)

    @staticmethod
    @pytest.fixture
    def playlist_unique(api_mock: SpotifyMock) -> dict[str, Any]:
        """Yields a response representing a uniquely named user playlist on Spotify"""
        names = [pl["name"] for pl in api_mock.user_playlists]
        return next(
            deepcopy(pl) for pl in api_mock.user_playlists
            if names.count(pl["name"]) == 1 and len(pl["name"]) != RemoteIDType.ID.value
        )

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    def test_get_playlist_url(self, playlist_unique: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        assert api.get_playlist_url(playlist=playlist_unique) == playlist_unique["href"]
        assert api.get_playlist_url(playlist=playlist_unique["name"]) == playlist_unique["href"]

        with pytest.raises(RemoteIDTypeError):
            api.get_playlist_url("does not exist")

    ###########################################################################
    ## POST playlist operations
    ###########################################################################
    def test_create_playlist(self, api: SpotifyAPI, api_mock: SpotifyMock):
        name = "test playlist"
        url = f"{api.api_url_base}/users/{api_mock.user_id}/playlists"
        result = api.create_playlist(name=name, public=False, collaborative=True)

        body = api_mock.get_requests(url=url, response={"name": name})[0].json()
        assert body["name"] == name
        assert PROGRAM_NAME in body["description"]
        assert not body["public"]
        assert body["collaborative"]
        assert result.removeprefix(f"{api.api_url_base}/playlists/").strip("/")

    def test_add_to_playlist_input_validation_and_skips(self, api: SpotifyAPI, api_mock: SpotifyMock):
        url = f"{api.api_url_base}/playlists/{random_id()}"
        for kind in ALL_ITEM_TYPES:
            if kind == ObjectType.TRACK:
                continue

            with pytest.raises(RemoteObjectTypeError):
                api.add_to_playlist(playlist=url, items=random_uris(kind=kind))

            with pytest.raises(RemoteObjectTypeError):
                api.add_to_playlist(playlist=url, items=random_api_urls(kind=kind))

            with pytest.raises(RemoteObjectTypeError):
                api.add_to_playlist(playlist=url, items=random_ext_urls(kind=kind))

        assert api.add_to_playlist(playlist=url, items=()) == 0

        with pytest.raises(RemoteIDTypeError):
            api.add_to_playlist(playlist="does not exist", items=random_ids())

    def test_add_to_playlist_batches_limited(self, playlist: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        id_list = random_ids(200, 300)
        valid_limit = 80

        api.add_to_playlist(playlist=playlist["href"], items=sample(id_list, k=10), limit=-30, skip_dupes=False)
        api.add_to_playlist(playlist=playlist["href"], items=id_list, limit=200, skip_dupes=False)
        api.add_to_playlist(playlist=playlist["href"], items=id_list, limit=valid_limit, skip_dupes=False)

        requests = api_mock.get_requests(url=playlist["href"] + "/tracks")

        for i, request in enumerate(requests, 1):
            count = len(request.json()["uris"])
            assert count >= 1
            assert count <= 100

    def test_add_to_playlist(self, playlist: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        total = playlist["tracks"]["total"]
        limit = total // 3
        assert total > limit  # ensure ranges are valid for test to work

        id_list = random_id_types(
            wrangler=api, kind=ObjectType.TRACK, start=total - api_mock.limit_lower, stop=total - 1
        )
        assert len(id_list) < total
        result = api.add_to_playlist(playlist=playlist["id"], items=id_list, limit=limit, skip_dupes=False)
        assert result == len(id_list)

        uris = []
        for request in api_mock.get_requests(url=playlist["href"] + "/tracks"):
            if not request.body:
                continue

            request_body = request.json()
            if "uris" in request_body:
                uris.extend(request_body["uris"])
        assert len(uris) == len(id_list)

    def test_add_to_playlist_with_skip(self, playlist: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api.extend_items(playlist["tracks"])
        api_mock.reset_mock()  # test checks the number of requests made

        initial = len(playlist["tracks"]["items"])
        total = playlist["tracks"]["total"]
        limit = total // 3
        assert total > limit  # ensure ranges are valid for test to work

        source = sample(playlist["tracks"]["items"], k=randrange(start=initial // 3, stop=initial // 2))
        id_list_dupes = [item["track"]["id"] for item in source]
        id_list_new = random_id_types(
            wrangler=api, kind=ObjectType.TRACK, start=api_mock.limit_lower, stop=randrange(20, 30)
        )

        result = api.add_to_playlist(playlist=playlist["uri"], items=id_list_dupes + id_list_new, limit=limit)
        assert result == len(id_list_new)

        uris = []
        for request in api_mock.get_requests(url=playlist["href"] + "/tracks"):
            if not request.body:
                continue

            request_body = request.json()
            if "uris" in request_body:
                uris.extend(request_body["uris"])
        assert len(uris) == len(id_list_new)

    ###########################################################################
    ## DELETE playlist operations
    ###########################################################################
    def test_delete_playlist(self, playlist_unique: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        result = api.delete_playlist(random_id_type(id_=playlist_unique["id"], wrangler=api, kind=ObjectType.PLAYLIST))
        assert result == playlist_unique["href"] + "/followers"

    def test_clear_from_playlist_input_validation_and_skips(self, api: SpotifyAPI, api_mock: SpotifyMock):
        url = f"{api.api_url_base}/playlists/{random_id()}"
        for kind in ALL_ITEM_TYPES:
            if kind == ObjectType.TRACK:
                continue

            with pytest.raises(RemoteObjectTypeError):
                api.clear_from_playlist(playlist=url, items=random_uris(kind=kind))

            with pytest.raises(RemoteObjectTypeError):
                api.clear_from_playlist(playlist=url, items=random_api_urls(kind=kind))

            with pytest.raises(RemoteObjectTypeError):
                api.clear_from_playlist(playlist=url, items=random_ext_urls(kind=kind))

        result = api.clear_from_playlist(playlist=url, items=())
        assert result == 0

        with pytest.raises(RemoteIDTypeError):
            api.add_to_playlist(playlist="does not exist", items=random_ids())

    def test_clear_from_playlist_batches_limited(
            self, playlist: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        id_list = random_ids(200, 300)
        valid_limit = 80

        api.clear_from_playlist(playlist=playlist["href"], items=sample(id_list, k=10), limit=-30)
        api.clear_from_playlist(playlist=playlist["href"], items=id_list, limit=valid_limit)
        api.clear_from_playlist(playlist=playlist["href"], items=id_list, limit=200)

        requests = [req.json() for req in api_mock.get_requests(url=playlist["href"] + "/tracks") if req.body]
        for i, body in enumerate(requests, 1):
            count = len(body["tracks"])
            assert count >= 1
            assert count <= 100

    def test_clear_from_playlist_items(self, playlist: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        total = playlist["tracks"]["total"]
        limit = total // 3
        assert total > limit  # ensure ranges are valid for test to work

        id_list = random_id_types(
            wrangler=api, kind=ObjectType.TRACK, start=total - api_mock.limit_lower, stop=total - 1
        )
        assert len(id_list) < total

        result = api.clear_from_playlist(playlist=playlist["uri"], items=id_list, limit=limit)
        assert result == len(id_list)

        requests = [req.json() for req in api_mock.get_requests(url=playlist["href"] + "/tracks") if req.body]
        assert all("tracks" in body for body in requests)
        assert len([uri["uri"] for req in requests for uri in req["tracks"]]) == len(id_list)

    def test_clear_from_playlist_all(self, playlist: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        total = playlist["tracks"]["total"]
        limit = total // 4
        assert total > limit  # ensure ranges are valid for test to work

        result = api.clear_from_playlist(playlist=playlist, limit=limit)
        assert result == total

        requests = [req.json() for req in api_mock.get_requests(url=playlist["href"] + "/tracks") if req.body]
        assert all("tracks" in body for body in requests)
        assert len([uri["uri"] for body in requests for uri in body["tracks"]]) == total
