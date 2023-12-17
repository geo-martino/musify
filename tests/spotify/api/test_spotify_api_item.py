from collections.abc import Collection
from copy import deepcopy
from itertools import batched
from random import sample, choice
from typing import Any
from urllib.parse import parse_qs

import pytest
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request

from syncify.remote.enums import RemoteItemType, RemoteIDType
from syncify.remote.exception import RemoteItemTypeError
from syncify.spotify.api import SpotifyAPI
from tests.remote.utils import random_id_type, random_id_types, ALL_ITEM_TYPES
from tests.spotify.api.mock import SpotifyMock, idfn
from tests.spotify.utils import random_ids, random_id, random_uri, random_api_url, random_ext_url
from tests.utils import random_str


class TestSpotifyAPIItems:
    """Tester for item-type endpoints of :py:class:`SpotifyAPI`"""

    @staticmethod
    def assert_item_types(results: list[dict[str, Any]], kind: RemoteItemType, kind_sub: str):
        """Loop through results and assert all items are of the correct type"""
        kind_sub = kind_sub.rstrip("s")
        for item in results:
            if kind == RemoteItemType.PLAYLIST:
                # playlist responses next items deeper under 'tracks' key
                assert item[kind_sub]["type"] == kind_sub
            else:
                assert item["type"] == kind_sub.rstrip("s")

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    @staticmethod
    def test_get_unit(api: SpotifyAPI):
        assert api._get_unit() == api.items_key
        assert api._get_unit(key="track") == "tracks"
        assert api._get_unit(unit="Audio Features") == "audio features"
        assert api._get_unit(unit="Audio Features", key="tracks") == "audio features"
        assert api._get_unit(key="audio-features") == "audio features"

    def test_get_items_batches_limited(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        kind = RemoteItemType.TRACK.name.casefold() + "s"
        url = f"{api.api_url_base}/{kind}"
        id_list = [track["id"] for track in spotify_mock.tracks]
        valid_limit = 30

        api._get_items_batched(url=url, id_list=sample(id_list, k=10), key=kind, limit=-30)
        api._get_items_batched(url=url, id_list=id_list, key=kind, limit=200)
        api._get_items_batched(url=url, id_list=id_list, key=kind, limit=valid_limit)

        for i, request in enumerate(spotify_mock.get_requests(url=url), 1):
            request_params = parse_qs(request.query)
            count = len(request_params["ids"][0].split(","))
            assert count >= 1
            assert count <= 50

    ###########################################################################
    ## Input validation
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

    @staticmethod
    def test_get_user_items_input_validation(api: SpotifyAPI):
        # raises error when invalid item type given
        for kind in set(ALL_ITEM_TYPES) - api.user_item_types:
            with pytest.raises(RemoteItemTypeError):
                api.get_user_items(kind=kind)

        # may only get valid user item types that are not playlists from the currently authenticated user
        for kind in api.user_item_types - {RemoteItemType.PLAYLIST}:
            with pytest.raises(RemoteItemTypeError):
                api.get_user_items(user=random_str(), kind=kind)

    @staticmethod
    def test_get_tracks_extra_input_validation(api: SpotifyAPI):
        assert api.get_tracks_extra(values=random_ids(), features=False, analysis=False) == {}
        assert api.get_tracks_extra(values=[], features=True, analysis=True) == {}

        value = api.convert(random_id(), kind=RemoteItemType.ALBUM, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        with pytest.raises(RemoteItemTypeError):
            api.get_tracks_extra(values=value, features=True)

    ###########################################################################
    ## Multi-, Batched-, and Extend tests for each supported item type
    ###########################################################################
    @staticmethod
    def assert_params(requests: list[Request], params: dict[str, Any] | list[dict[str, Any]]):
        """Check for expected params from get item endpoint functions"""
        for request in requests:
            request_params = parse_qs(request.query)
            if isinstance(params, list):
                assert any(request_params[k][0] == param[k] for param in params for k in param)
                continue

            for k, v in params.items():
                assert k in request_params
                assert request_params[k][0] == params[k]

    # TODO: expand to test for all RemoteItemTypes
    @pytest.mark.parametrize("kind", [
        RemoteItemType.PLAYLIST, RemoteItemType.TRACK, RemoteItemType.ALBUM, RemoteItemType.ARTIST, RemoteItemType.USER,
    ], ids=idfn)
    def test_get_item_multi(self, kind: RemoteItemType, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        unit = kind.name.casefold() + "s"
        url = f"{api.api_url_base}/{unit}"
        params = {"key": "value"}

        source = spotify_mock.item_type_map[kind]
        source = sample(source, k=10) if len(source) > 10 else source
        source_map = {item["id"]: item for item in source}
        id_list = [item["id"] for item in source]

        results = api._get_items_multi(url=url, id_list=id_list, params=params, key=None)
        requests = spotify_mock.get_requests(url=url)

        self.assert_results(expected=source_map, results=results, kind=kind)
        self.assert_params(requests=requests, params=params)
        # appropriate number of requests were made for multi requests
        assert sum(len(spotify_mock.get_requests(url=f"{url}/{id_}")) for id_ in id_list) == len(source)

    @pytest.mark.parametrize("kind", [
        RemoteItemType.TRACK, RemoteItemType.ALBUM, RemoteItemType.ARTIST,
    ], ids=idfn)
    def test_get_item_batched(self, kind: RemoteItemType, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        unit = kind.name.casefold() + "s"
        url = f"{api.api_url_base}/{unit}"
        params = {"key": "value"}

        source = spotify_mock.item_type_map[kind]
        source_map = {item["id"]: item for item in source}
        id_list = [item["id"] for item in source]
        limit = len(source) // 3  # force pagination
        assert len(source) > limit  # ensure ranges are valid for test to work

        results = api._get_items_batched(url=url, id_list=id_list, params=params, key=unit, limit=limit)
        requests = spotify_mock.get_requests(url=url)

        self.assert_results(expected=source_map, results=results, kind=kind)
        self.assert_params(requests=requests, params=params)

        # appropriate number of requests were made for batched requests
        id_params = [{"ids": ",".join(ids)} for ids in batched(id_list, limit)]
        requests = [req for req in requests if "ids" in parse_qs(req.query)]
        assert len(requests) == len(id_params)
        self.assert_params(requests=requests, params=id_params)

    # TODO: expand to test for all expandable RemoteItemTypes
    @pytest.mark.parametrize("kind", [
        RemoteItemType.PLAYLIST, RemoteItemType.ALBUM
    ], ids=idfn)
    def test_extend_items(self, kind: RemoteItemType, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        unit_main = kind.name.casefold() + "s"
        unit_sub = api.collection_item_map.get(kind, kind).name.casefold() + "s"

        source = next(item[unit_sub] for item in spotify_mock.item_type_map[kind] if item[unit_sub]["total"] > 3)
        total = source["total"]
        limit = source["total"] // 3  # force pagination

        test = spotify_mock.format_items_block(
            url=source["href"], items=source[api.items_key][:limit], limit=limit, total=source["total"]
        )

        # assert test value generated correctly and ranges are valid for test to work
        assert source["total"] == test["total"]
        assert test["total"] > test["limit"]
        assert test["total"] > len(test[api.items_key])

        results = api._extend_items(items_block=test, unit_main=unit_main, unit_sub=unit_sub)
        requests = spotify_mock.get_requests(url=source["href"].split("?")[0])

        # assert extension to total
        assert len(results) == total
        assert len(test[api.items_key]) == total
        assert test[api.items_key] == results  # extension happened to input value and results match input
        self.assert_item_types(results=test[api.items_key], kind=kind, kind_sub=unit_sub)

        # appropriate number of requests made (minus 1 for initial input)
        assert len(requests) == total // limit + ((total / limit) % 1 > 0) - 1

    ###########################################################################
    ## Get user items
    ###########################################################################
    # TODO: expand to test for all possible RemoteItemTypes
    @pytest.mark.parametrize("kind,user", [
        (RemoteItemType.PLAYLIST, False),
        (RemoteItemType.PLAYLIST, True),
        (RemoteItemType.TRACK, False),
        (RemoteItemType.ALBUM, False),
        (RemoteItemType.ARTIST, False),
        # (RemoteItemType.AUDIOBOOK, False),
        # (RemoteItemType.SHOW, False),
        # (RemoteItemType.EPISODE, False),
    ], ids=idfn)
    def test_get_user_items(
            self, kind: RemoteItemType, user: bool, api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        test = None
        if user:
            test = random_id_type(id_=spotify_mock.user_id, wrangler=api, kind=RemoteItemType.USER)
            url = f"{api.api_url_base}/users/{spotify_mock.user_id}/{kind.name.casefold()}s"
        elif kind == RemoteItemType.ARTIST:
            url = f"{api.api_url_base}/me/following"
        else:
            url = f"{api.api_url_base}/me/{kind.name.casefold()}s"

        source = spotify_mock.item_type_map_user[kind]
        source_map = {item["id"] if "id" in item else item[kind.name.casefold()]["id"]: item for item in source}
        total = len(source)
        limit = total // 3  # force pagination
        assert total > limit  # ensure ranges are valid for test to work

        results = api.get_user_items(user=test, kind=kind, limit=limit)
        assert len(results) == total

        # appropriate number of requests made
        requests = [req for req in spotify_mock.get_requests(url=url)]
        assert len(requests) == total // limit + ((total / limit) % 1 > 0)

        for result in results:  # check results are as expected
            if kind not in {RemoteItemType.PLAYLIST, RemoteItemType.ARTIST}:
                assert "added_at" in result
                result = result[kind.name.casefold()]
                assert result == source_map[result["id"]][kind.name.casefold()]
            else:
                assert result == source_map[result["id"]]

    ###########################################################################
    ## Get items - assertions
    ###########################################################################
    def assert_results(
            self,
            expected: dict[str, dict[str, Any]],
            results: list[dict[str, Any]],
            kind: RemoteItemType,
            kind_sub: str | None = None,
    ) -> None:
        """Check results have expected values"""
        if kind_sub is None:
            assert len(results) == len(expected)

        for result in results:
            assert result["type"] == kind.name.casefold()

            if kind_sub is None:
                # item get with no extension, result should match source
                assert result == expected[result["id"]]
                continue

            # extended collection assertions
            assert result["id"] in expected
            assert len(result[kind_sub]["items"]) == expected[result["id"]][kind_sub]["total"]
            self.assert_item_types(results=result[kind_sub]["items"], kind=kind, kind_sub=kind_sub)

    @staticmethod
    def assert_calls(
            expected: Collection[dict[str, Any]],
            requests: list[Request],
            kind_sub: str | None = None,
            limit: int | None = None,
    ):
        """Assert an appropriate number of calls were made for multi- or batch- call functions"""
        initial_calls = len(list(batched(expected, limit))) if limit else len(expected)
        extend_calls = 0
        if kind_sub:
            for expect in expected:
                # minus 1 for initial call to get the collection
                pages = expect[kind_sub]["total"] / expect[kind_sub]["limit"] - 1
                extend_calls += int(pages) + (pages % 1 > 0)

        assert len(requests) == initial_calls + extend_calls

    @staticmethod
    def assert_update(
            expected: list[dict[str, Any]],
            results: list[dict[str, Any]],
            test: dict[str, dict[str, Any]],
            kind: RemoteItemType,
            kind_sub: str | None = None,
    ):
        """Assert the originally input ``test`` API response values were updated by the operation"""
        assert len(results) == len(expected)
        for result, actual, expect in zip(results, test.values(), expected):
            if not kind_sub:
                assert result == actual
                continue

            expected_total = expect[kind_sub]["total"]
            expected_no_items = {k: v for k, v in expect.items() if k != kind_sub}
            assert result["type"] == kind.name.casefold()

            assert len(result[kind_sub]["items"]) == expected_total
            assert len(actual[kind_sub]["items"]) == expected_total

            assert {k: v for k, v in result.items() if k != kind_sub} == expected_no_items
            assert {k: v for k, v in actual.items() if k != kind_sub} == expected_no_items
            assert result == actual

    ###########################################################################
    ## Get user items - tests
    ###########################################################################
    # TODO: expand to test for all RemoteItemTypes
    @pytest.mark.parametrize("kind,enrich_keys", [
        (RemoteItemType.PLAYLIST, {"description", "followers", "images", "public"}),
        (RemoteItemType.TRACK, {"artists", "album"}),
        (RemoteItemType.ALBUM, {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}),
        (RemoteItemType.ARTIST, {"followers", "genres", "images", "popularity"}),
        (RemoteItemType.USER, {"display_name", "followers", "images", "product"}),
    ], ids=idfn)
    def test_get_items_single(
            self, kind: RemoteItemType, enrich_keys: set[str], api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        extend = kind in api.collection_item_map
        kind_sub = api.collection_item_map[kind].name.casefold() + "s" if extend else None

        source = choice(spotify_mock.item_type_map[kind])
        test = random_id_type(id_=source["id"], wrangler=api, kind=kind)

        results = api.get_items(values=test, kind=kind, extend=extend)
        self.assert_results(expected={source["id"]: source}, results=results, kind=kind, kind_sub=kind_sub)

        # appropriate number of requests made
        url = f"{api.api_url_base}/{kind.name.casefold()}s/{source["id"]}"
        requests = spotify_mock.get_requests(url=url)
        if kind_sub:
            requests += spotify_mock.get_requests(url=f"{url}/{kind_sub}")
        self.assert_calls(expected=[source], requests=requests, kind_sub=kind_sub, limit=None)

        # test input map is updated when API response is given
        test = {k: v for k, v in source.items() if k not in enrich_keys}
        # check source and test are different, skip comparing on 'kind_sub' key for performance
        expected_no_items = {k: v for k, v in source.items() if k != kind_sub}
        assert {k: v for k, v in test.items() if k != kind_sub} != expected_no_items

        results = api.get_items(values=test)
        self.assert_update(expected=[source], results=results, test={test["id"]: test}, kind=kind, kind_sub=kind_sub)

        # just check that these don't fail
        api.get_items(values=source["uri"])
        api.get_items(values=source["href"])
        api.get_items(values=source["external_urls"]["spotify"])

    @pytest.mark.parametrize("kind,enrich_keys", [
        (RemoteItemType.PLAYLIST, {"description", "followers", "images", "public"}),
        (RemoteItemType.TRACK, {"artists", "album"}),
        (RemoteItemType.ALBUM, {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}),
        (RemoteItemType.ARTIST, {"followers", "genres", "images", "popularity"}),
        (RemoteItemType.USER, {"display_name", "followers", "images", "product"}),
    ], ids=idfn)
    def test_get_items_many(
            self, kind: RemoteItemType, enrich_keys: set[str], api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        extend = kind in api.collection_item_map
        kind_sub = api.collection_item_map[kind].name.casefold() + "s" if extend else None

        source = spotify_mock.item_type_map[kind]
        source = sample(source, 10) if len(source) > 10 else source
        source_map = {item["id"]: item for item in source}
        test = random_id_types(id_list=source_map, wrangler=api, kind=kind)

        # force pagination
        limit = len(source) // 3 if kind not in {RemoteItemType.PLAYLIST, RemoteItemType.USER} else None
        if limit is not None:  # ensure ranges are valid for test to work
            assert len(source) > limit

        results = api.get_items(values=test, kind=kind, limit=limit if limit else 50, extend=extend)
        self.assert_results(expected=source_map, results=results, kind=kind, kind_sub=kind_sub)

        # appropriate number of requests made
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        requests = spotify_mock.get_requests(url=url)
        for item in source:
            if kind in {RemoteItemType.USER, RemoteItemType.PLAYLIST}:
                requests += spotify_mock.get_requests(url=f"{url}/{item["id"]}")
            if kind_sub:
                requests += spotify_mock.get_requests(url=f"{url}/{item["id"]}/{kind_sub}")
        self.assert_calls(expected=source, requests=requests, kind_sub=kind_sub, limit=limit)

        # test input maps are updated when API responses are given
        test = {id_: {k: v for k, v in item.items() if k not in enrich_keys} for id_, item in source_map.items()}
        for item in source:  # check source and test are different, skip comparing on 'kind_sub' key for performance
            source_no_items = {k: v for k, v in item.items() if k != kind_sub}
            assert {k: v for k, v in test[item["id"]].items() if k != kind_sub} != source_no_items

        results = api.get_items(values=test.values())
        self.assert_update(expected=source, results=results, test=test, kind=kind, kind_sub=kind_sub)

    ###########################################################################
    ## get_tracks_extra tests
    ###########################################################################
    def test_get_tracks_extra_single(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        source = choice(spotify_mock.tracks)
        source_features = spotify_mock.audio_features[source["id"]]
        source_analysis = spotify_mock.audio_analysis[source["id"]]
        test = random_id_type(id_=source["id"], wrangler=api, kind=RemoteItemType.TRACK)

        results = api.get_tracks_extra(values=test, features=True, analysis=True)
        assert set(results) == {"audio_features", "audio_analysis"}
        assert results["audio_features"][0] == source_features
        assert results["audio_analysis"][0] == source_analysis

        # appropriate number of requests made
        requests = spotify_mock.get_requests(url=f"{api.api_url_base}/audio-features/{source["id"]}")
        requests += spotify_mock.get_requests(url=f"{api.api_url_base}/audio-analysis/{source["id"]}")
        assert len(requests) == 2

        # test input map is updated when API response is given
        test = deepcopy(source)
        assert "audio_features" not in test
        assert "audio_analysis" not in test

        results = api.get_tracks_extra(values=test, features=True, analysis=False)
        assert len(results) == 1
        assert test["audio_features"] == source_features
        assert "audio_analysis" not in test

        results = api.get_tracks_extra(values=test, features=False, analysis=True)
        assert len(results) == 1
        assert test["audio_features"] == source_features
        assert test["audio_analysis"] == source_analysis

        # just check that these don't fail
        api.get_tracks_extra(values=source["uri"])
        api.get_tracks_extra(values=source["href"])
        api.get_tracks_extra(values=source["external_urls"]["spotify"])

    def test_get_tracks_extra_many(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        source = spotify_mock.tracks
        source = sample(source, 10) if len(source) > 10 else source
        source_map = {item["id"]: item for item in source}
        source_features = {item["id"]: spotify_mock.audio_features[item["id"]] for item in source}
        source_analysis = {item["id"]: spotify_mock.audio_analysis[item["id"]] for item in source}
        test = random_id_types(id_list=source_map, wrangler=api, kind=RemoteItemType.TRACK)

        limit = len(source) // 3  # force pagination
        assert len(source) > limit  # ensure ranges are valid for test to work

        results = api.get_tracks_extra(values=test, features=True, analysis=True, limit=limit)

        assert set(results) == {"audio_features", "audio_analysis"}
        for result in results["audio_features"]:
            assert result == source_features[result["id"]]
        for result, expected in zip(results["audio_analysis"], source_analysis.values()):
            assert result == expected

        # appropriate number of requests made
        requests = spotify_mock.get_requests(url=f"{api.api_url_base}/audio-features")
        for item in source:
            requests += spotify_mock.get_requests(url=f"{api.api_url_base}/audio-analysis/{item["id"]}")
        assert len(spotify_mock.request_history) == len(list(batched(test, limit))) + len(test)

        # test input maps are updated when API responses are given
        test = deepcopy(source_map)
        for item in test.values():
            assert "audio_features" not in item
            assert "audio_analysis" not in item

        results = api.get_tracks_extra(values=test.values(), features=True, analysis=False)
        assert len(results) == 1
        for id_, item in test.items():
            assert item["audio_features"] == source_features[id_]
            assert "audio_analysis" not in item

        results = api.get_tracks_extra(values=test.values(), features=False, analysis=True)
        assert len(results) == 1
        for id_, item in test.items():
            assert item["audio_features"] == source_features[id_]
            assert item["audio_analysis"] == source_analysis[id_]

    def test_get_tracks(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        source = choice(spotify_mock.tracks)

        test = random_id_type(id_=source["id"], wrangler=api, kind=RemoteItemType.TRACK)
        results = api.get_tracks(values=test, features=True, analysis=True)
        assert {k: v for k, v in results[0].items() if k not in {"audio_features", "audio_analysis"}} == source
        assert "audio_features" not in test
        assert "audio_analysis" not in test

        test = deepcopy(source)
        assert "audio_features" not in test
        assert "audio_analysis" not in test

        results = api.get_tracks(values=test, features=True, analysis=True)
        assert {k: v for k, v in results[0].items() if k not in {"audio_features", "audio_analysis"}} == source
        assert "audio_features" in test
        assert "audio_analysis" in test
