import re
from itertools import batched
from random import randrange, choice
from typing import Any
from urllib.parse import urlparse, parse_qs

import pytest
from requests_mock.mocker import Mocker
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember
from requests_mock.response import _Context as Context

from syncify.api.exception import APIError
from syncify.remote.enums import RemoteItemType, RemoteIDType
from syncify.remote.exception import RemoteItemTypeError
from syncify.spotify.api import SpotifyAPI
from syncify.utils import UnitIterable
from tests.spotify.api.base_tester import SpotifyAPITesterHelpers
from tests.spotify.api.utils import SpotifyTestResponses as Responses
from tests.spotify.utils import random_ids, random_id


class SpotifyAPIItemsTester(SpotifyAPITesterHelpers):
    """Tester for item-type endpoints of :py:class:`SpotifyAPI`"""

    item_multi_call_kinds = {RemoteItemType.USER, RemoteItemType.PLAYLIST}

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    @staticmethod
    def test_get_unit(api: SpotifyAPI):
        assert api._get_unit() == "items"
        assert api._get_unit(key="track") == "tracks"
        assert api._get_unit(unit="Audio Features") == "audio features"
        assert api._get_unit(unit="Audio Features", key="tracks") == "audio features"
        assert api._get_unit(key="audio-features") == "audio features"

    @staticmethod
    def test_get_items_batched_limits_limit(api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.TRACK.name.casefold() + "s"
        items = [Responses.track(album=True, artists=True) for _ in range(randrange(10, 30))]
        item_map = {item["id"]: item for item in items}
        url = f"{api.api_url_base}/{kind}"

        def get_expected_json_batched(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected response"""
            id_list = parse_qs(urlparse(req.url).query)["ids"][0].split(",")
            return {kind: [item_map[id_] for id_ in id_list]}

        requests_mock.get(url=re.compile(url + r"?"), json=get_expected_json_batched)

        def test_limit(limit: int):
            api._get_items_batched(
                url=url, id_list=item_map.keys(), key=kind, limit=limit, use_cache=False
            )
            for request in requests_mock.request_history:
                request_params = parse_qs(urlparse(request.url).query)
                assert len(request_params["ids"][0].split(",")) >= 1
                assert len(request_params["ids"][0].split(",")) <= 50

        test_limit(-10)
        test_limit(200)

    @staticmethod
    def test_get_items_fails(api: SpotifyAPI, requests_mock: Mocker):
        url = f"{api.api_url_base}/tracks"

        requests_mock.get(url=re.compile(url + r"/"), json={"tracks": []})
        with pytest.raises(APIError):
            api._get_items_multi(url=url, id_list=random_ids(), key="playlists", use_cache=False)

        requests_mock.get(url=re.compile(url + r"?"), json={"tracks": []})
        with pytest.raises(APIError):
            api._get_items_batched(url=url, id_list=random_ids(), key="playlists", use_cache=False)

    ###########################################################################
    ## Multi and Batched tests for each supported item type
    ###########################################################################
    # noinspection PyProtectedMember
    def item_result_test(self, api: SpotifyAPI, kind: str, items: list[dict[str, Any]], requests_mock: Mocker) -> None:
        """Run tests on single and batched item endpoint functions"""
        url = f"{api.api_url_base}/{kind}"
        params = {"key": "value"}
        item_map = {item["id"]: item for item in items}

        # multiple single calls test
        def get_expected_json_multi(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected response"""
            id_ = req.url.split("?")[0].split("/")[-1]
            return item_map[id_]

        requests_mock.get(url=re.compile(url + r"/"), json=get_expected_json_multi)
        response = api._get_items_multi(url=url, id_list=item_map.keys(), params=params, key=None, use_cache=False)
        self.assert_expected_items_response(
            response=response, params=params, kind=kind, items=items, requests_mock=requests_mock
        )
        assert len(requests_mock.request_history) == len(items)

        # batched calls test
        def get_expected_json_batched(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected response"""
            id_list = parse_qs(urlparse(req.url).query)["ids"][0].split(",")
            return {kind: [item_map[id_] for id_ in id_list]}

        limit = len(items) // 3

        requests_mock.reset_mock()
        requests_mock.get(url=re.compile(url + r"?"), json=get_expected_json_batched)
        response = api._get_items_batched(
            url=url, id_list=item_map.keys(), params=params, key=kind, limit=limit, use_cache=False
        )
        self.assert_expected_items_response(
            response=response, params=params, kind=kind, items=items, requests_mock=requests_mock
        )

        id_chunks = list(batched(item_map.keys(), limit))
        assert len(requests_mock.request_history) == len(id_chunks)

        for request, id_chunk in zip(requests_mock.request_history, id_chunks):
            request_params = parse_qs(urlparse(request.url).query)
            assert "ids" in request_params
            assert request_params["ids"][0].split(",") == list(id_chunk)

    @staticmethod
    def assert_expected_items_response(
            response:  list[dict[str, Any]],
            params: dict[str, Any],
            kind: str,
            items: list[dict[str, Any]],
            requests_mock: Mocker,
    ):
        """Run assertions on response from get item endpoint functions"""
        assert response == items
        for r in response:
            assert r["type"] == kind.rstrip("s")

        for request in requests_mock.request_history:
            request_params = parse_qs(urlparse(request.url).query)
            assert "key" in params
            assert request_params["key"][0] == params["key"]

    def test_get_track_item_results(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.TRACK.name.casefold() + "s"
        items = [Responses.track(album=True, artists=True) for _ in range(randrange(10, 30))]
        self.item_result_test(api=api, kind=kind, items=items, requests_mock=requests_mock)

    def test_get_artist_item_results(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.ARTIST.name.casefold() + "s"
        items = [Responses.artist(extend=True) for _ in range(randrange(5, 20))]
        self.item_result_test(api=api, kind=kind, items=items, requests_mock=requests_mock)

    def test_get_album_item_results(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.ALBUM.name.casefold() + "s"
        items = [Responses.album(extend=True, artists=True, tracks=True) for _ in range(randrange(5, 20))]
        self.item_result_test(api=api, kind=kind, items=items, requests_mock=requests_mock)

    def test_get_playlist_item_results(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.PLAYLIST.name.casefold() + "s"
        items = [Responses.playlist(tracks=True) for _ in range(randrange(5, 20))]
        self.item_result_test(api=api, kind=kind, items=items, requests_mock=requests_mock)

    ###########################################################################
    ## get_items input types tests
    ###########################################################################
    def test_get_items_input_validation(self, api: SpotifyAPI):
        with pytest.raises(RemoteItemTypeError):
            api.get_items(values=random_ids(), kind=None)
            api.get_items(values=self.random_id_type(api=api, kind=RemoteItemType.TRACK), kind=RemoteItemType.SHOW)

    def test_get_items_on_single_string(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = choice([i for i in RemoteItemType.all() if i not in self.item_multi_call_kinds])
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        value = self.random_id_type(api=api, kind=kind)

        requests_mock.get(url=re.compile(url + "/"), json={"type": kind.name.casefold()})
        response = api.get_items(values=value, kind=kind, use_cache=False)

        assert len(response) == 1
        assert len(requests_mock.request_history) == 1
        assert response[0]["type"] == kind.name.casefold()

    def test_get_items_on_many_strings(self, api: SpotifyAPI, requests_mock: Mocker):
        # this test also checks that the function calls the appropriate API call method

        for kind in self.item_multi_call_kinds:
            url = f"{api.api_url_base}/{kind.name.casefold()}s"
            values = self.random_id_types(api=api, kind=kind, start=1, stop=10)

            requests_mock.reset_mock()
            requests_mock.get(url=re.compile(url + "/"), json={"type": kind.name.casefold()})
            response = api.get_items(values=values, kind=kind, use_cache=False)

            assert len(response) == len(values)
            assert len(requests_mock.request_history) == len(values)
            for r in response:
                assert r["type"] == kind.name.casefold()

        def get_expected_json_batched(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected response"""
            req_parsed = urlparse(req.url)
            req_kind = req_parsed.path.split("/")[-1]
            id_list = parse_qs(req_parsed.query)["ids"][0].split(",")
            return {req_kind: [{"id": id_, "type": req_kind.rstrip("s")} for id_ in id_list]}

        for kind in RemoteItemType.all():
            if kind in self.item_multi_call_kinds:
                continue

            url = f"{api.api_url_base}/{kind.name.casefold()}s"
            values = self.random_id_types(api=api, kind=kind, start=10, stop=30)
            limit = len(values) // 3

            requests_mock.reset_mock()
            requests_mock.get(url=re.compile(url + "?"), json=get_expected_json_batched)
            response = api.get_items(values=values, kind=kind, limit=limit, use_cache=False)

            assert len(response) == len(values)
            id_chunks = list(batched(values, limit))
            assert len(requests_mock.request_history) == len(id_chunks)
            for r in response:
                assert r["type"] == kind.name.casefold()

    def test_get_items_updates_input(self, api: SpotifyAPI, requests_mock: Mocker):
        expected = Responses.album(extend=True, artists=True, tracks=True)
        self.get_items_api_response_input_test(api=api, expected=expected, requests_mock=requests_mock)

        expected = [Responses.album(extend=True, artists=True, tracks=True) for _ in range(randrange(5, 10))]
        self.get_items_api_response_input_test(api=api, expected=expected, requests_mock=requests_mock)

    @staticmethod
    def get_items_api_response_input_test(
            api: SpotifyAPI, expected: UnitIterable[dict[str, Any]], requests_mock: Mocker
    ):
        """Test to check whether an input API response to py:meth:`get_items` is updated with new results"""
        kind = RemoteItemType.ALBUM
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        extended_keys = {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}

        if isinstance(expected, dict):
            values = {k: v for k, v in expected.items() if k not in extended_keys}
            mock_response = expected
        else:
            assert len(expected) > 1
            values = [{k: v for k, v in item.items() if k not in extended_keys} for item in expected]
            mock_response = {"albums": expected}

        requests_mock.get(url=re.compile(url), json=mock_response)
        response = api.get_items(values=values, kind=kind, use_cache=False)

        if isinstance(expected, dict):
            assert len(response) == 1
            assert response[0] == expected
            assert all(key in values for key in extended_keys)
        else:
            for res, exp, val in zip(response, expected, values):
                assert res == exp
                assert all(key in val for key in extended_keys)

    ###########################################################################
    ## get_tracks_extra tests
    ###########################################################################
    @staticmethod
    def test_get_tracks_extra_input_validation(api: SpotifyAPI):
        assert api.get_tracks_extra(values=random_ids(), features=False, analysis=False) == {}
        assert api.get_tracks_extra(values=[], features=True, analysis=True) == {}

        value = api.convert(random_id(), kind=RemoteItemType.ALBUM, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        with pytest.raises(RemoteItemTypeError):
            api.get_tracks_extra(values=value, features=True)

    def test_get_tracks_extra_single_string(self, api: SpotifyAPI, requests_mock: Mocker):
        id_ = random_id()
        value = self.random_id_type(id_=id_, api=api, kind=RemoteItemType.TRACK)

        duration = 2079598
        expected_features = Responses.audio_features(track_id=id_, duration_ms=duration)
        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-features"), json=expected_features)
        expected_analysis = {"track": {"duration": duration / 1000}}
        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-analysis"), json=expected_analysis)

        response = api.get_tracks_extra(values=value, features=True, analysis=True, use_cache=False)

        assert len(response) == 2
        assert len(requests_mock.request_history) == 2
        assert len(response["audio_features"]) == 1
        assert response["audio_features"][0] == expected_features
        assert len(response["audio_analysis"]) == 1
        assert response["audio_analysis"][0] == expected_analysis

    def test_get_tracks_extra_many_strings(self, api: SpotifyAPI, requests_mock: Mocker):
        # this test also checks that the function calls the appropriate API call method
        kind = RemoteItemType.TRACK
        id_list = random_ids(5, 20)

        values = self.random_id_types(api=api, kind=kind, id_list=id_list, start=1, stop=10)
        expected_features = {"audio_features": [Responses.audio_features(track_id=id_) for id_ in id_list]}
        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-features"), json=expected_features)
        expected_analysis = {"track": {"duration": randrange(0, int(10e6)) / 1000}}
        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-analysis"), json=expected_analysis)

        response = api.get_tracks_extra(values=values, features=True, analysis=True, limit=50, use_cache=False)

        assert len(response) == 2
        assert len(requests_mock.request_history) == 1 + len(id_list)
        assert len(response["audio_features"]) == len(id_list)
        assert response["audio_features"] == expected_features["audio_features"]
        assert len(response["audio_analysis"]) == len(id_list)
        assert response["audio_analysis"] == [expected_analysis for _ in range(len(id_list))]

    def test_get_tracks_extra_updates_input(self, api: SpotifyAPI, requests_mock: Mocker):
        expected = Responses.track(album=False, artists=False)
        self.get_tracks_extra_api_response_input_test(api=api, expected=expected, requests_mock=requests_mock)

        expected = [Responses.track(album=False, artists=False) for _ in range(randrange(5, 10))]
        self.get_tracks_extra_api_response_input_test(api=api, expected=expected, requests_mock=requests_mock)

    @staticmethod
    def get_tracks_extra_api_response_input_test(
            api: SpotifyAPI, expected: UnitIterable[dict[str, Any]], requests_mock: Mocker
    ):
        """Test to check whether an input API response to  py:meth:`get_tracks_extra` is updated with new results"""
        extended_keys = {"audio_features", "audio_analysis"}

        if isinstance(expected, dict):
            values = {k: v for k, v in expected.items() if k not in extended_keys}
            expected_features = Responses.audio_features(track_id=expected["id"], duration_ms=expected["duration_ms"])
        else:
            assert len(expected) > 1
            id_list = [track["id"] for track in expected]
            values = [{k: v for k, v in item.items() if k not in extended_keys} for item in expected]
            expected_features = {"audio_features": [Responses.audio_features(track_id=id_) for id_ in id_list]}

        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-features"), json=expected_features)
        response = api.get_tracks_extra(values=values, features=True, analysis=False, limit=50, use_cache=False)

        assert len(response) == 1
        if isinstance(expected, dict):
            assert response["audio_features"][0] == expected_features
            assert values["audio_features"] == expected_features
        else:
            for res, exp, val in zip(response["audio_features"], expected_features["audio_features"], values):
                assert res == exp
                assert val["audio_features"] == exp

    def test_get_tracks(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.TRACK

        expected_track = Responses.track(album=False, artists=False)
        id_ = expected_track["id"]
        duration = expected_track["duration_ms"]
        value = self.random_id_type(id_=id_, api=api, kind=kind)

        requests_mock.get(url=re.compile(f"{api.api_url_base}/tracks/"), json=expected_track)
        expected_features = Responses.audio_features(track_id=id_, duration_ms=duration / 1000)
        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-features"), json=expected_features)
        expected_analysis = {"track": {"duration": duration / 1000}}
        requests_mock.get(url=re.compile(f"{api.api_url_base}/audio-analysis"), json=expected_analysis)

        response = api.get_tracks(values=value, features=True, analysis=True, use_cache=False)
        assert response[0]["id"] == expected_track["id"]
        assert response[0]["audio_features"] == expected_features
        assert response[0]["audio_analysis"] == expected_analysis
        assert "audio_features" not in expected_track
        assert "audio_analysis" not in expected_track

        response = api.get_tracks(values=expected_track, features=True, analysis=True, use_cache=False)
        assert response == expected_track
        assert expected_track["audio_features"] == expected_features
        assert expected_track["audio_analysis"] == expected_analysis
