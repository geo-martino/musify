import re
from collections.abc import Callable
from copy import copy
from functools import partial
from itertools import batched
from random import randrange
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
from tests.spotify.api.utils import SpotifyTestResponses as Responses, random_id_type, random_id_types, ALL_ITEM_TYPES
from tests.spotify.utils import random_ids, random_id, random_uri, random_api_url, random_ext_url

ITEM_MULTI_CALL_KINDS = {RemoteItemType.USER, RemoteItemType.PLAYLIST}
ITEM_BATCH_CALL_KINDS = set(ALL_ITEM_TYPES) - ITEM_MULTI_CALL_KINDS


class TestSpotifyAPIItems:
    """Tester for item-type endpoints of :py:class:`SpotifyAPI`"""

    @staticmethod
    def get_items_json_response(
            req: Request, _: Context, item_map: dict[str, dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Dynamically generate expected response for multi- and batched-call items"""
        req_parsed = urlparse(req.url)
        req_params = parse_qs(req_parsed.query)

        if "ids" in req_params:  # batched call
            req_kind = req_parsed.path.split("/")[-1]
            id_list = req_params["ids"][0].split(",")

            if item_map:
                return {req_kind: [item_map[id_] for id_ in id_list]}
            return {req_kind: [{"id": id_, "type": req_kind.rstrip("s")} for id_ in id_list]}
        else:  # multi call
            path_parts = req_parsed.path.split("/")
            req_kind = path_parts[-2]
            id_ = path_parts[-1]

            if item_map:
                return item_map[id_]
            return {"id": id_, "type": req_kind.rstrip("s")}

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

    def test_get_items_batched_limits_batches(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.TRACK.name.casefold() + "s"
        url = f"{api.api_url_base}/{kind}"

        requests_mock.get(url=re.compile(url + r"\?"), json=self.get_items_json_response)

        def test_batch_limited(limit: int):
            api._get_items_batched(url=url, id_list=random_ids(), key=kind, limit=limit)
            for request in requests_mock.request_history:
                request_params = parse_qs(urlparse(request.url).query)
                assert len(request_params["ids"][0].split(",")) >= 1
                assert len(request_params["ids"][0].split(",")) <= 50

        test_batch_limited(-10)
        test_batch_limited(200)

    @staticmethod
    def test_get_items_fails(api: SpotifyAPI, requests_mock: Mocker):
        url = f"{api.api_url_base}/tracks"

        requests_mock.get(url=re.compile(url + r"/"), json={"tracks": []})
        with pytest.raises(APIError):
            api._get_items_multi(url=url, id_list=random_ids(), key="playlists")

        requests_mock.get(url=re.compile(url + r"\?"), json={"tracks": []})
        with pytest.raises(APIError):
            api._get_items_batched(url=url, id_list=random_ids(), key="playlists")

    ###########################################################################
    ## Multi and Batched tests for each supported item type
    ###########################################################################
    # TODO: expand to test for all RemoteItemTypes
    @pytest.mark.parametrize("kind,item_getter", [
        (RemoteItemType.PLAYLIST, partial(Responses.playlist, tracks=True)),
        (RemoteItemType.TRACK, partial(Responses.track, album=True, artists=True)),
        (RemoteItemType.ARTIST, partial(Responses.artist, extend=True)),
        (RemoteItemType.ALBUM, partial(Responses.album, extend=True, artists=True, tracks=True)),
        (RemoteItemType.USER, partial(Responses.user)),
        # (RemoteItemType.SHOW, partial()),
        # (RemoteItemType.EPISODE, partial()),
        # (RemoteItemType.AUDIOBOOK, partial()),
        # (RemoteItemType.CHAPTER, partial()),
    ])
    def test_item_result(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            item_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker,
    ):
        kind = kind.name.casefold() + "s"
        url = f"{api.api_url_base}/{kind}"
        params = {"key": "value"}

        items = [item_getter() for _ in range(randrange(5, 20))]
        item_map = {item["id"]: item for item in items}

        # multi-call test
        response_getter = partial(self.get_items_json_response, item_map=item_map)
        requests_mock.get(url=re.compile(url + r"/"), json=response_getter)

        results = api._get_items_multi(url=url, id_list=item_map.keys(), params=params, key=None)

        self.assert_expected_items_response(
            results=results, params=params, kind=kind, items=items, requests_mock=requests_mock
        )
        assert len(requests_mock.request_history) == len(items)

        # batch-call test
        requests_mock.reset_mock()
        response_getter = partial(self.get_items_json_response, item_map=item_map)
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)
        limit = len(items) // 3

        results = api._get_items_batched(url=url, id_list=item_map.keys(), params=params, key=kind, limit=limit)

        self.assert_expected_items_response(
            results=results, params=params, kind=kind, items=items, requests_mock=requests_mock
        )
        id_chunks = list(batched(item_map.keys(), limit))
        assert len(requests_mock.request_history) == len(id_chunks)

        for request, id_chunk in zip(requests_mock.request_history, id_chunks):
            request_params = parse_qs(urlparse(request.url).query)
            assert "ids" in request_params
            assert request_params["ids"][0].split(",") == list(id_chunk)

    @staticmethod
    def assert_expected_items_response(
            results:  list[dict[str, Any]],
            params: dict[str, Any],
            kind: str,
            items: list[dict[str, Any]],
            requests_mock: Mocker,
    ):
        """Run assertions on response from get item endpoint functions"""
        assert results == items
        for result in results:
            assert result["type"] == kind.rstrip("s")

        for request in requests_mock.request_history:
            request_params = parse_qs(urlparse(request.url).query)
            assert "key" in params
            assert request_params["key"][0] == params["key"]

    ###########################################################################
    ## get_items input types tests
    ###########################################################################
    @staticmethod
    def test_get_items_input_validation(api: SpotifyAPI):
        with pytest.raises(RemoteItemTypeError):
            api.get_items(values=random_ids(), kind=None)
        with pytest.raises(RemoteItemTypeError):
            api.get_items(values=random_uri(kind=RemoteItemType.TRACK), kind=RemoteItemType.SHOW)
        with pytest.raises(RemoteItemTypeError):
            api.get_items(values=random_api_url(kind=RemoteItemType.ARTIST), kind=RemoteItemType.PLAYLIST)
        with pytest.raises(RemoteItemTypeError):
            api.get_items(values=random_ext_url(kind=RemoteItemType.CHAPTER), kind=RemoteItemType.AUDIOBOOK)

    # TODO: expand to test for all RemoteItemTypes
    @pytest.mark.parametrize("kind,item_getter", [
        (RemoteItemType.PLAYLIST, partial(Responses.playlist, tracks=True)),
        (RemoteItemType.TRACK, partial(Responses.track, album=True, artists=True)),
        (RemoteItemType.ALBUM, partial(Responses.album, extend=True, artists=True, tracks=True)),
        (RemoteItemType.ARTIST, partial(Responses.artist, extend=True)),
        (RemoteItemType.USER, partial(Responses.user)),
        # (RemoteItemType.SHOW, partial()),
        # (RemoteItemType.EPISODE, partial()),
        # (RemoteItemType.AUDIOBOOK, partial()),
        # (RemoteItemType.CHAPTER, partial()),
    ])
    def test_get_items_on_single_string(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            item_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker,
    ):
        url = f"{api.api_url_base}/{kind.name.casefold()}s"

        item_source = item_getter()
        item_test = random_id_type(api=api, kind=kind)

        requests_mock.get(url=re.compile(url + "/"), json=item_source)
        results = api.get_items(values=item_test, kind=kind)

        assert len(results) == 1
        assert len(requests_mock.request_history) == 1
        assert results[0]["type"] == kind.name.casefold()
        assert results[0] == item_source

        # just check that these don't fail
        api.get_items(values=random_uri(kind=kind))
        api.get_items(values=random_api_url(kind=kind))
        api.get_items(values=random_ext_url(kind=kind))

    @pytest.mark.parametrize("kind,item_getter", [
        (RemoteItemType.PLAYLIST, partial(Responses.playlist, tracks=True)),
        (RemoteItemType.USER, partial(Responses.user)),
    ])
    def test_get_items_on_many_strings_multi(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            item_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker,
    ):
        # this test also checks that the function calls the appropriate API call method
        url = f"{api.api_url_base}/{kind.name.casefold()}s"

        items_source = [item_getter() for _ in range(randrange(5, 10))]
        item_map = {str(item["id"]): item for item in items_source}
        items_test = random_id_types(id_list=item_map, api=api, kind=kind)

        response_getter = partial(self.get_items_json_response, item_map=item_map)
        requests_mock.get(url=re.compile(url + "/"), json=response_getter)
        results = api.get_items(values=items_test, kind=kind)

        assert len(results) == len(items_test)
        assert len(requests_mock.request_history) == len(items_test)
        for result in results:
            assert result["type"] == kind.name.casefold()
            assert result == item_map[result["id"]]

    # TODO: expand to test for all RemoteItemTypes
    @pytest.mark.parametrize("kind,item_getter", [
        (RemoteItemType.TRACK, partial(Responses.track, album=True, artists=True)),
        (RemoteItemType.ALBUM, partial(Responses.album, extend=True, artists=True, tracks=True)),
        (RemoteItemType.ARTIST, partial(Responses.artist, extend=True)),
        # (RemoteItemType.SHOW, partial()),
        # (RemoteItemType.EPISODE, partial()),
        # (RemoteItemType.AUDIOBOOK, partial()),
        # (RemoteItemType.CHAPTER, partial()),
    ])
    def test_get_items_on_many_strings_batched(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            item_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker,
    ):
        # this test also checks that the function calls the appropriate API call method
        url = f"{api.api_url_base}/{kind.name.casefold()}s"

        items_source = [item_getter() for _ in range(randrange(10, 30))]
        item_map = {str(item["id"]): item for item in items_source}
        items_test = random_id_types(id_list=item_map, api=api, kind=kind)
        limit = len(items_test) // 3

        response_getter = partial(self.get_items_json_response, item_map=item_map)
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)
        results = api.get_items(values=items_test, kind=kind, limit=limit)

        assert len(results) == len(items_test)
        assert len(requests_mock.request_history) == len(list(batched(items_test, limit)))
        for result in results:
            assert result["type"] == kind.name.casefold()
            assert result == item_map[result["id"]]

    def test_get_items_updates_input_single(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.ALBUM
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        extended_keys = {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}

        item_source = Responses.album(extend=True, artists=True, tracks=True)
        item_test = {k: v for k, v in item_source.items() if k not in extended_keys}
        assert item_test != item_source

        requests_mock.get(url=re.compile(url), json=item_source)
        results = api.get_items(values=item_test)

        assert len(results) == 1
        assert results[0]["type"] == kind.name.casefold()
        assert results[0] == item_source
        assert item_test == item_source

    def test_get_items_updates_input_many(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.ALBUM
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        extended_keys = {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}

        items_source = [Responses.album(extend=True, artists=True, tracks=True) for _ in range(randrange(5, 10))]
        item_map = {str(item["id"]): copy(item) for item in items_source}
        items_test = {id_: {k: v for k, v in item.items() if k not in extended_keys} for id_, item in item_map.items()}

        requests_mock.get(url=re.compile(url), json={"albums": items_source})
        results = api.get_items(values=list(items_test.values()))

        for result in results:
            item_test = items_test[result["id"]]
            item_expected = item_map[result["id"]]
            assert result["type"] == kind.name.casefold()
            assert result == item_expected
            assert item_test == item_expected

    ###########################################################################
    ## get_tracks_extra tests
    ###########################################################################

    track_extra_keys = {"audio_features", "audio_analysis"}

    @staticmethod
    def get_audio_features_json_response(
            req: Request, _: Context, item_map: dict[str, dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Dynamically generate expected response for audio-features endpoint"""
        req_parsed = urlparse(req.url)
        req_params = parse_qs(req_parsed.query)

        if "ids" in req_params:  # batched call
            id_list = req_params["ids"][0].split(",")
            if item_map:
                items = [item_map[id_]["audio_features"] for id_ in id_list]
            else:
                items = [Responses.audio_features(track_id=id_) for id_ in id_list]
            return {"audio_features": items}
        else:  # multi call
            id_ = req.url.split("?")[0].split("/")[-1]
            if item_map:
                return item_map[id_]["audio_features"]
            return Responses.audio_features(track_id=id_)

    @staticmethod
    def get_audio_analysis_json_response(
            req: Request, __: Context, item_map: dict[str, dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Dynamically generate expected response for audio-analysis endpoint"""
        if item_map:
            id_ = req.url.split("?")[0].split("/")[-1]
            return item_map[id_]["audio_analysis"]
        return {"track": {}}

    def apply_tracks_extra_mock(
            self, api: SpotifyAPI, requests_mock: Mocker, item_map: dict[str, dict[str, Any]] | None = None
    ) -> None:
        """Yield a requests_mock that is set to give dummy responses for audio features and analysis endpoints"""
        for item in item_map.values():
            item["audio_features"] = Responses.audio_features(track_id=item["id"], duration_ms=item["duration_ms"])
            item["audio_analysis"] = {"track": {"duration": item["duration_ms"] / 1000}}

        features_url = re.compile(f"{api.api_url_base}/audio-features")
        features_response_getter = partial(self.get_audio_features_json_response, item_map=item_map)
        requests_mock.get(url=features_url, json=features_response_getter)

        analysis_url = re.compile(f"{api.api_url_base}/audio-analysis")
        analysis_response_getter = partial(self.get_audio_analysis_json_response, item_map=item_map)
        requests_mock.get(url=analysis_url, json=analysis_response_getter)

    @staticmethod
    def test_get_tracks_extra_input_validation(api: SpotifyAPI):
        assert api.get_tracks_extra(values=random_ids(), features=False, analysis=False) == {}
        assert api.get_tracks_extra(values=[], features=True, analysis=True) == {}

        value = api.convert(random_id(), kind=RemoteItemType.ALBUM, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        with pytest.raises(RemoteItemTypeError):
            api.get_tracks_extra(values=value, features=True)

    def test_get_tracks_extra_single_string(self, api: SpotifyAPI, requests_mock: Mocker):
        item_source = Responses.track(album=True, artists=True)
        item_map = {item_source["id"]: copy(item_source)}
        item_test = random_id_type(id_=item_source["id"], api=api, kind=RemoteItemType.TRACK)

        self.apply_tracks_extra_mock(api=api, requests_mock=requests_mock, item_map=item_map)
        item_expected = item_map[item_source["id"]]  # get back enriched item
        results = api.get_tracks_extra(values=item_test, features=True, analysis=True)

        assert set(results) == self.track_extra_keys
        assert len(requests_mock.request_history) == 2
        assert results["audio_features"][0] == item_expected["audio_features"]
        assert results["audio_analysis"][0] == item_expected["audio_analysis"]

    def test_get_tracks_extra_many_strings(self, api: SpotifyAPI, requests_mock: Mocker):
        items_source = [Responses.track(album=True, artists=True) for _ in range(randrange(10, 30))]
        item_map = {str(item["id"]): copy(item) for item in items_source}
        items_test = random_id_types(id_list=item_map, api=api, kind=RemoteItemType.TRACK)
        limit = len(items_test) // 3

        self.apply_tracks_extra_mock(api=api, requests_mock=requests_mock, item_map=item_map)
        results = api.get_tracks_extra(values=items_test, features=True, analysis=True, limit=limit)

        assert set(results) == self.track_extra_keys
        assert len(requests_mock.request_history) == len(list(batched(items_test, limit))) + len(items_source)

        for result in results["audio_features"]:
            item_expected = item_map[result["id"]]
            assert result == item_expected["audio_features"]
        for result, item_expected in zip(results["audio_analysis"], item_map.values()):
            assert result == item_expected["audio_analysis"]

    def test_get_tracks_extra_updates_input_single(self, api: SpotifyAPI, requests_mock: Mocker):
        item_source = Responses.track(album=True, artists=True)
        item_map = {item_source["id"]: copy(item_source)}
        item_test = {k: v for k, v in item_source.items() if k not in self.track_extra_keys}

        self.apply_tracks_extra_mock(api=api, requests_mock=requests_mock, item_map=item_map)
        item_expected = item_map[item_source["id"]]  # get back enriched item
        results = api.get_tracks_extra(values=item_test, features=True, analysis=False, limit=50)

        assert set(results) == {"audio_features"}
        assert len(requests_mock.request_history) == 1
        assert results["audio_features"][0] == item_expected["audio_features"]
        assert item_test["audio_features"] == item_expected["audio_features"]
        assert "audio_analysis" not in item_test

    def test_get_tracks_extra_updates_input_many(self, api: SpotifyAPI, requests_mock: Mocker):
        items_source = [Responses.track(album=True, artists=True) for _ in range(randrange(10, 30))]
        item_map = {str(item["id"]): copy(item) for item in items_source}
        items_test = {id_: {k: v for k, v in item.items() if k not in self.track_extra_keys}
                      for id_, item in item_map.items()}
        limit = len(items_test) // 3

        self.apply_tracks_extra_mock(api=api, requests_mock=requests_mock, item_map=item_map)
        results = api.get_tracks_extra(values=list(items_test.values()), features=True, analysis=False, limit=limit)

        assert set(results) == {"audio_features"}
        assert len(requests_mock.request_history) == len(list(batched(items_test, limit)))

        for result in results["audio_features"]:
            item_test = items_test[result["id"]]
            item_expected = item_map[result["id"]]
            assert result == item_expected["audio_features"]
            assert item_test["audio_features"] == item_expected["audio_features"]
            assert "audio_analysis" not in item_test

    def test_get_tracks(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.TRACK
        url = f"{api.api_url_base}/{kind.name.casefold()}s"

        item_source = Responses.track(album=True, artists=True)
        item_map = {item_source["id"]: copy(item_source)}
        item_test = {k: v for k, v in item_source.items() if k not in self.track_extra_keys}
        item_test_value = random_id_type(id_=item_source["id"], api=api, kind=kind)

        self.apply_tracks_extra_mock(api=api, requests_mock=requests_mock, item_map=item_map)
        item_expected = item_map[item_source["id"]]  # get back enriched item
        requests_mock.get(url=re.compile(url), json=item_source)

        results = api.get_tracks(values=item_test_value, features=True, analysis=True)
        assert results[0] == item_expected
        assert item_source != item_expected
        assert item_test != item_expected
        assert "audio_features" not in item_test
        assert "audio_analysis" not in item_test

        results = api.get_tracks(values=item_test, features=True, analysis=True)
        assert results[0] == item_expected
        assert item_source != item_expected
        assert item_test == item_expected
        assert "audio_features" in item_test
        assert "audio_analysis" in item_test
