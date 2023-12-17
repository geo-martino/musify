from random import randrange, sample
from typing import Any
from urllib.parse import parse_qs

import pytest
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember
from requests_mock.response import _Context as Context

from syncify import PROGRAM_NAME
from syncify.remote.enums import RemoteItemType
from syncify.remote.exception import RemoteItemTypeError, RemoteIDTypeError
from syncify.spotify.api import SpotifyAPI
from tests.remote.utils import random_id_type, random_id_types, ALL_ITEM_TYPES
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.utils import random_id, random_ids, random_uris, random_api_urls, random_ext_urls


class TestSpotifyAPIPlaylists:
    """Tester for playlist modification type endpoints of :py:class:`SpotifyAPI`"""

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    def test_get_playlist_url(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        playlist = spotify_mock.user_playlists[0]

        assert api.get_playlist_url(playlist=playlist) == playlist["href"]
        assert api.get_playlist_url(playlist=playlist["name"]) == playlist["href"]

        with pytest.raises(RemoteIDTypeError):
            api.get_playlist_url("does not exist")

    ###########################################################################
    ## POST playlist operations
    ###########################################################################
    @staticmethod
    def test_create_playlist(api: SpotifyAPI, spotify_mock: SpotifyMock):
        name = "test playlist"

        def response_getter(req: Request, _: Context) -> dict[str, Any]:
            """Process body and generate playlist response data"""
            data = req.json()

            assert data["name"] == name
            assert PROGRAM_NAME in data["description"]
            assert not data["public"]
            assert data["collaborative"]

            response = spotify_mock.generate_playlist(api=api, item_count=0)
            response["name"] = data["name"]
            response["description"] = data["description"]
            response["public"] = data["public"]
            response["collaborative"] = data["collaborative"]

            return response

        url = f"{api.api_url_base}/users/{spotify_mock.user_id}/playlists"
        spotify_mock.post(url=url, json=response_getter)
        result = api.create_playlist(name=name, public=False, collaborative=True)

        body = spotify_mock.get_requests(url=url, response={"name": name})[0].json()
        assert body["name"] == name
        assert PROGRAM_NAME in body["description"]
        assert not body["public"]
        assert body["collaborative"]
        assert result.replace(f"{api.api_url_base}/playlists/", "").strip("/")

    def test_add_to_playlist_input_validation_and_skips(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        url = f"{api.api_url_base}/playlists/{random_id()}"
        for kind in ALL_ITEM_TYPES:
            if kind == RemoteItemType.TRACK:
                continue

            with pytest.raises(RemoteItemTypeError):
                api.add_to_playlist(playlist=url, items=random_uris(kind=kind))

            with pytest.raises(RemoteItemTypeError):
                api.add_to_playlist(playlist=url, items=random_api_urls(kind=kind))

            with pytest.raises(RemoteItemTypeError):
                api.add_to_playlist(playlist=url, items=random_ext_urls(kind=kind))

        assert api.add_to_playlist(playlist=url, items=()) == 0

        with pytest.raises(RemoteIDTypeError):
            api.add_to_playlist(playlist="does not exist", items=random_ids())

    def test_add_to_playlist_batches_limited(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        playlist = spotify_mock.user_playlists[0]
        id_list = random_ids(200, 300)
        valid_limit = 80

        api.add_to_playlist(playlist=playlist["href"], items=sample(id_list, k=10), limit=-30, skip_dupes=False)
        api.add_to_playlist(playlist=playlist["href"], items=id_list, limit=200, skip_dupes=False)
        api.add_to_playlist(playlist=playlist["href"], items=id_list, limit=valid_limit, skip_dupes=False)

        requests = spotify_mock.get_requests(url=playlist["href"] + "/tracks")

        for i, request in enumerate(requests, 1):
            request_params = parse_qs(request.query)
            count = len(request_params["uris"][0].split(","))
            assert count >= 1
            assert count <= 100

    def test_add_to_playlist(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        playlist = spotify_mock.user_playlists[1]
        total = playlist["tracks"]["total"]
        limit = total // 3

        id_list = random_id_types(wrangler=api, kind=RemoteItemType.TRACK, start=total - 30, stop=total - 1)
        assert len(id_list) < total
        result = api.add_to_playlist(playlist=playlist["id"], items=id_list, limit=limit, skip_dupes=False)
        assert result == len(id_list)

        uris = []
        for request in spotify_mock.get_requests(url=playlist["href"] + "/tracks"):
            request_params = parse_qs(request.query)
            if "uris" in request_params:
                uris.extend(request_params["uris"][0].split(","))
        assert len(uris) == len(id_list)

    def test_add_to_playlist_with_skip(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        playlist = spotify_mock.playlists[2]
        total = playlist["tracks"]["total"]
        limit = total // 3
        available = len(playlist["tracks"]["items"])

        track_sample = sample(playlist["tracks"]["items"], k=randrange(start=available // 3, stop=available // 2))
        id_list_dupes = [track["track"]["id"] for track in track_sample]
        id_list_new = random_id_types(wrangler=api, kind=RemoteItemType.TRACK, start=10, stop=randrange(20, 30))
        id_list = id_list_dupes + id_list_new

        result = api.add_to_playlist(playlist=playlist["uri"], items=id_list, limit=limit)
        assert result == len(id_list_new)

        uris = []
        for request in spotify_mock.get_requests(url=playlist["href"] + "/tracks"):
            request_params = parse_qs(request.query)
            if "uris" in request_params:
                uris.extend(request_params["uris"][0].split(","))
        assert len(uris) == len(id_list_new)

    ###########################################################################
    ## DELETE playlist operations
    ###########################################################################
    def test_delete_playlist(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        playlist = spotify_mock.user_playlists[0]
        result = api.delete_playlist(random_id_type(id_=playlist["id"], wrangler=api, kind=RemoteItemType.PLAYLIST))
        assert result == playlist["href"] + "/followers"

    def test_clear_from_playlist_input_validation_and_skips(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        url = f"{api.api_url_base}/playlists/{random_id()}"
        for kind in ALL_ITEM_TYPES:
            if kind == RemoteItemType.TRACK:
                continue

            with pytest.raises(RemoteItemTypeError):
                api.clear_from_playlist(playlist=url, items=random_uris(kind=kind))

            with pytest.raises(RemoteItemTypeError):
                api.clear_from_playlist(playlist=url, items=random_api_urls(kind=kind))

            with pytest.raises(RemoteItemTypeError):
                api.clear_from_playlist(playlist=url, items=random_ext_urls(kind=kind))

        result = api.clear_from_playlist(playlist=url, items=())
        assert result == 0

        with pytest.raises(RemoteIDTypeError):
            api.add_to_playlist(playlist="does not exist", items=random_ids())

    def test_clear_from_playlist_batches_limited(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        playlist = spotify_mock.playlists[0]
        id_list = random_ids(200, 300)
        valid_limit = 80

        api.clear_from_playlist(playlist=playlist["href"], items=sample(id_list, k=10), limit=-30)
        api.clear_from_playlist(playlist=playlist["href"], items=id_list, limit=valid_limit)
        api.clear_from_playlist(playlist=playlist["href"], items=id_list, limit=200)

        requests = [req.json() for req in spotify_mock.get_requests(url=playlist["href"] + "/tracks") if req.body]
        for i, body in enumerate(requests, 1):
            count = len(body["tracks"])
            assert count >= 1
            assert count <= 100

    def test_clear_from_playlist_items(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        playlist = spotify_mock.playlists[1]
        total = playlist["tracks"]["total"]
        limit = total // 3

        id_list = random_id_types(wrangler=api, kind=RemoteItemType.TRACK, start=total - 30, stop=total - 1)
        assert len(id_list) < total

        result = api.clear_from_playlist(playlist=playlist["uri"], items=id_list, limit=limit)
        assert result == len(id_list)

        requests = [req.json() for req in spotify_mock.get_requests(url=playlist["href"] + "/tracks") if req.body]
        assert all("tracks" in body for body in requests)
        assert len([uri["uri"] for req in requests for uri in req["tracks"]]) == len(id_list)

    def test_clear_from_playlist_all(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        playlist = spotify_mock.playlists[2]
        total = playlist["tracks"]["total"]
        limit = total // 4

        result = api.clear_from_playlist(playlist=playlist, limit=limit)
        assert result == total

        requests = [req.json() for req in spotify_mock.get_requests(url=playlist["href"] + "/tracks") if req.body]
        assert all("tracks" in body for body in requests)
        assert len([uri["uri"] for body in requests for uri in body["tracks"]]) == total
