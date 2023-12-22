from collections.abc import Collection
from copy import deepcopy
from itertools import batched
from random import sample, choice
from typing import Any
from urllib.parse import parse_qs

import pytest
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request

from syncify.remote.enums import RemoteObjectType as ObjectType, RemoteIDType as IDType
from syncify.remote.exception import RemoteObjectTypeError
from syncify.spotify.api import SpotifyAPI
from tests.remote.utils import random_id_type, random_id_types, ALL_ITEM_TYPES
from tests.spotify.api.mock import SpotifyMock, idfn
from tests.spotify.utils import random_ids, random_id, random_uri, random_api_url, random_ext_url
from tests.utils import random_str


class TestSpotifyAPIItems:
    """Tester for item-type endpoints of :py:class:`SpotifyAPI`"""

    @staticmethod
    def assert_item_types(results: list[dict[str, Any]], kind: ObjectType, key: str):
        """Loop through results and assert all items are of the correct type"""
        key = key.rstrip("s")
        for result in results:
            if kind == ObjectType.PLAYLIST:
                # playlist responses next items deeper under 'tracks' key
                assert result[key]["type"] == key
            else:
                assert result["type"] == key.rstrip("s")

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    def test_get_unit(self, api: SpotifyAPI):
        assert api._get_unit() == api.items_key
        assert api._get_unit(key="track") == "tracks"
        assert api._get_unit(unit="Audio Features") == "audio features"
        assert api._get_unit(unit="Audio Features", key="tracks") == "audio features"
        assert api._get_unit(key="audio-features") == "audio features"

    def test_get_items_batches_limited(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        key = ObjectType.TRACK.name.casefold() + "s"
        url = f"{api.api_url_base}/{key}"
        id_list = [track["id"] for track in spotify_mock.tracks]
        valid_limit = 30

        api._get_items_batched(url=url, id_list=sample(id_list, k=10), key=key, limit=-30)
        api._get_items_batched(url=url, id_list=id_list, key=key, limit=200)
        api._get_items_batched(url=url, id_list=id_list, key=key, limit=valid_limit)

        for request in spotify_mock.get_requests(url=url):
            request_params = parse_qs(request.query)
            count = len(request_params["ids"][0].split(","))
            assert count >= 1
            assert count <= 50

    ###########################################################################
    ## Input validation
    ###########################################################################
    def test_get_items_input_validation(self, api: SpotifyAPI):
        with pytest.raises(RemoteObjectTypeError):
            api.get_items(values=random_ids(), kind=None)
        with pytest.raises(RemoteObjectTypeError):
            api.get_items(values=random_uri(kind=ObjectType.TRACK), kind=ObjectType.SHOW)
        with pytest.raises(RemoteObjectTypeError):
            api.get_items(values=random_api_url(kind=ObjectType.ARTIST), kind=ObjectType.PLAYLIST)
        with pytest.raises(RemoteObjectTypeError):
            api.get_items(values=random_ext_url(kind=ObjectType.CHAPTER), kind=ObjectType.AUDIOBOOK)

    def test_get_user_items_input_validation(self, api: SpotifyAPI):
        # raises error when invalid item type given
        for kind in set(ALL_ITEM_TYPES) - api.user_item_types:
            with pytest.raises(RemoteObjectTypeError):
                api.get_user_items(kind=kind)

        # may only get valid user item types that are not playlists from the currently authorised user
        for kind in api.user_item_types - {ObjectType.PLAYLIST}:
            with pytest.raises(RemoteObjectTypeError):
                api.get_user_items(user=random_str(), kind=kind)

    def test_get_tracks_extra_input_validation(self, api: SpotifyAPI):
        assert api.get_tracks_extra(values=random_ids(), features=False, analysis=False) == {}
        assert api.get_tracks_extra(values=[], features=True, analysis=True) == {}

        value = api.convert(random_id(), kind=ObjectType.ALBUM, type_in=IDType.ID, type_out=IDType.URL)
        with pytest.raises(RemoteObjectTypeError):
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

    # TODO: expand mock to allow testing for all RemoteObjectTypes
    @pytest.mark.parametrize("kind", [
        ObjectType.PLAYLIST,
        ObjectType.TRACK,
        ObjectType.ALBUM,
        ObjectType.ARTIST,
        ObjectType.USER,
        # ObjectType.SHOW,
        # ObjectType.EPISODE,
        # ObjectType.AUDIOBOOK,
        # ObjectType.CHAPTER,
    ], ids=idfn)
    def test_get_item_multi(self, kind: ObjectType, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        url = f"{api.api_url_base}/{kind.name.casefold()}s"
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

    # TODO: expand mock to allow testing for all RemoteObjectTypes
    @pytest.mark.parametrize("kind", [
        ObjectType.TRACK,
        ObjectType.ALBUM,
        ObjectType.ARTIST,
        # ObjectType.SHOW,
        # ObjectType.EPISODE,
        # ObjectType.AUDIOBOOK,
        # ObjectType.CHAPTER,
    ], ids=idfn)
    def test_get_item_batched(self, kind: ObjectType, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        key = kind.name.casefold() + "s"
        url = f"{api.api_url_base}/{key}"
        params = {"key": "value"}

        source = spotify_mock.item_type_map[kind]
        source_map = {item["id"]: item for item in source}
        id_list = [item["id"] for item in source]
        limit = min(len(source) // 3, 50)  # force pagination
        assert len(source) > limit  # ensure ranges are valid for test to work

        results = api._get_items_batched(url=url, id_list=id_list, params=params, key=key, limit=limit)
        requests = spotify_mock.get_requests(url=url)

        self.assert_results(expected=source_map, results=results, kind=kind)
        self.assert_params(requests=requests, params=params)

        # appropriate number of requests were made for batched requests
        id_params = [{"ids": ",".join(ids)} for ids in batched(id_list, limit)]
        requests = [req for req in requests if "ids" in parse_qs(req.query)]
        assert len(requests) == len(id_params)
        self.assert_params(requests=requests, params=id_params)

    # TODO: expand mock to allow testing for all extendable RemoteObjectTypes
    @pytest.mark.parametrize("kind", [
        ObjectType.PLAYLIST, ObjectType.ALBUM,  # ObjectType.SHOW, ObjectType.AUDIOBOOK,
    ], ids=idfn)
    def test_extend_items(self, kind: ObjectType, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        key = api.collection_item_map.get(kind, kind).name.casefold() + "s"
        source = next(item[key] for item in spotify_mock.item_type_map[kind] if item[key]["total"] > 3)
        total = source["total"]
        limit = min(source["total"] // 3, len(source[api.items_key]) // 3, 50)  # force pagination
        items = source[api.items_key][:limit]

        test = spotify_mock.format_items_block(url=source["href"], items=items, limit=limit, total=source["total"])

        # assert ranges are valid for test to work and test value generated correctly
        assert len(source[api.items_key]) > limit
        assert len(items) <= limit
        assert source["total"] == test["total"]
        assert test["total"] > test["limit"]
        assert test["total"] > len(test[api.items_key])

        results = api.extend_items(items_block=test, unit=kind.name.casefold() + "s", key=key)
        requests = spotify_mock.get_requests(url=source["href"].split("?")[0])

        # assert extension to total
        assert len(results) == total
        assert len(test[api.items_key]) == total
        assert test[api.items_key] == results  # extension happened to input value and results match input
        self.assert_item_types(results=test[api.items_key], kind=kind, key=key)

        # appropriate number of requests made (minus 1 for initial input)

        assert len(requests) == spotify_mock.calculate_pages(limit=limit, total=total) - 1

    ###########################################################################
    ## Get user items
    ###########################################################################
    # TODO: expand mock to allow testing for all RemoteObjectTypes
    @pytest.mark.parametrize("kind,user", [
        (ObjectType.PLAYLIST, False),
        (ObjectType.PLAYLIST, True),
        (ObjectType.TRACK, False),
        (ObjectType.ALBUM, False),
        (ObjectType.ARTIST, False),
        # (ObjectType.AUDIOBOOK, False),
        # (ObjectType.SHOW, False),
        # (ObjectType.EPISODE, False),
    ], ids=idfn)
    def test_get_user_items(
            self, kind: ObjectType, user: bool, api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        test = None
        if user:
            test = random_id_type(id_=spotify_mock.user_id, wrangler=api, kind=ObjectType.USER)
            url = f"{api.api_url_base}/users/{spotify_mock.user_id}/{kind.name.casefold()}s"
        elif kind == ObjectType.ARTIST:
            url = f"{api.api_url_base}/me/following"
        else:
            url = f"{api.api_url_base}/me/{kind.name.casefold()}s"

        source = spotify_mock.item_type_map_user[kind]
        source_map = {item["id"] if "id" in item else item[kind.name.casefold()]["id"]: item for item in source}
        total = len(source)
        limit = min(total // 3, 50)  # force pagination
        assert total > limit  # ensure ranges are valid for test to work

        results = api.get_user_items(user=test, kind=kind, limit=limit)
        assert len(results) == total

        # appropriate number of requests made
        requests = [req for req in spotify_mock.get_requests(url=url)]
        assert len(requests) == spotify_mock.calculate_pages(limit=limit, total=total)

        for result in results:  # check results are as expected
            if kind not in {ObjectType.PLAYLIST, ObjectType.ARTIST}:
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
            kind: ObjectType,
            key: str | None = None,
    ) -> None:
        """Check results have expected values"""
        if key is None:
            assert len(results) == len(expected)

        for result in results:
            assert result["type"] == kind.name.casefold()

            if key is None:
                # item get with no extension, result should match source
                assert result == expected[result["id"]]
                continue

            # extended collection assertions
            assert result["id"] in expected
            assert len(result[key]["items"]) == expected[result["id"]][key]["total"]
            self.assert_item_types(results=result[key]["items"], kind=kind, key=key)

    @staticmethod
    def assert_calls(
            expected: Collection[dict[str, Any]],
            requests: list[Request],
            spotify_mock: SpotifyMock,
            key: str | None = None,
            limit: int | None = None,
    ):
        """Assert an appropriate number of calls were made for multi- or batch- call functions"""
        initial_calls = len(list(batched(expected, limit))) if limit else len(expected)
        extend_calls = 0
        if key:
            # minus 1 for initial call to get the collection
            extend_calls += sum(spotify_mock.calculate_pages_from_response(expect) - 1 for expect in expected)

        assert len(requests) == initial_calls + extend_calls

    @staticmethod
    def assert_update(
            expected: list[dict[str, Any]],
            results: list[dict[str, Any]],
            test: dict[str, dict[str, Any]],
            kind: ObjectType,
            key: str | None = None,
    ):
        """Assert the originally input ``test`` API response values were updated by the operation"""
        assert len(results) == len(expected)
        for result, actual, expect in zip(results, test.values(), expected):
            if not key:
                assert result == actual
                continue

            expected_total = expect[key]["total"]
            expected_no_items = {k: v for k, v in expect.items() if k != key}
            assert result["type"] == kind.name.casefold()

            assert len(result[key]["items"]) == expected_total
            assert len(actual[key]["items"]) == expected_total

            assert {k: v for k, v in result.items() if k != key} == expected_no_items
            assert {k: v for k, v in actual.items() if k != key} == expected_no_items
            assert result == actual

    ###########################################################################
    ## Get user items - tests
    ###########################################################################
    # TODO: expand mock to allow testing for all RemoteObjectTypes
    @pytest.mark.parametrize("kind,update_keys", [
        (ObjectType.PLAYLIST, {"description", "followers", "images", "public"}),
        (ObjectType.TRACK, {"artists", "album"}),
        (ObjectType.ALBUM, {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}),
        (ObjectType.ARTIST, {"followers", "genres", "images", "popularity"}),
        (ObjectType.USER, {"display_name", "followers", "images", "product"}),
        # (ObjectType.SHOW, {}),
        # (ObjectType.EPISODE, {}),
        # (ObjectType.AUDIOBOOK, {}),
        # (ObjectType.CHAPTER, {}),
    ], ids=idfn)
    def test_get_items_single(
            self, kind: ObjectType, update_keys: set[str], api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        extend = kind in api.collection_item_map
        key = api.collection_item_map[kind].name.casefold() + "s" if extend else None

        source = choice(spotify_mock.item_type_map[kind])
        test = random_id_type(id_=source["id"], wrangler=api, kind=kind)

        results = api.get_items(values=test, kind=kind, extend=extend)
        self.assert_results(expected={source["id"]: source}, results=results, kind=kind, key=key)

        # appropriate number of requests made
        url = f"{api.api_url_base}/{kind.name.casefold()}s/{source["id"]}"
        requests = spotify_mock.get_requests(url=url)
        if key:
            requests += spotify_mock.get_requests(url=f"{url}/{key}")
        self.assert_calls(expected=[source], requests=requests, key=key, limit=None, spotify_mock=spotify_mock)

        # test input map is updated when API response is given
        test = {k: v for k, v in source.items() if k not in update_keys}
        # check source and test are different, skip comparing on 'kind_sub' key for performance
        expected_no_items = {k: v for k, v in source.items() if k != key}
        assert {k: v for k, v in test.items() if k != key} != expected_no_items

        results = api.get_items(values=test)
        self.assert_update(expected=[source], results=results, test={test["id"]: test}, kind=kind, key=key)

        # just check that these don't fail
        api.get_items(values=source["uri"])
        api.get_items(values=source["href"])
        api.get_items(values=source["external_urls"]["spotify"])

    # TODO: expand mock to allow testing for all RemoteObjectTypes
    @pytest.mark.parametrize("kind,update_keys", [
        (ObjectType.PLAYLIST, {"description", "followers", "images", "public"}),
        (ObjectType.TRACK, {"artists", "album"}),
        (ObjectType.ALBUM, {"artists", "tracks", "copyrights", "external_ids", "genres", "label", "popularity"}),
        (ObjectType.ARTIST, {"followers", "genres", "images", "popularity"}),
        (ObjectType.USER, {"display_name", "followers", "images", "product"}),
        # (ObjectType.SHOW, {}),
        # (ObjectType.EPISODE, {}),
        # (ObjectType.AUDIOBOOK, {}),
        # (ObjectType.CHAPTER, {}),
    ], ids=idfn)
    def test_get_items_many(
            self, kind: ObjectType, update_keys: set[str], api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        extend = kind in api.collection_item_map
        key = api.collection_item_map[kind].name.casefold() + "s" if extend else None

        source = spotify_mock.item_type_map[kind]
        source = sample(source, 10) if len(source) > 10 else source
        source_map = {item["id"]: item for item in source}
        test = random_id_types(id_list=source_map, wrangler=api, kind=kind)

        # force pagination
        limit = len(source) // 3 if kind not in {ObjectType.PLAYLIST, ObjectType.USER} else None
        if limit is not None:  # ensure ranges are valid for test to work
            assert len(source) > limit

        results = api.get_items(values=test, kind=kind, limit=limit or 50, extend=extend)
        self.assert_results(expected=source_map, results=results, kind=kind, key=key)

        # appropriate number of requests made
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        requests = spotify_mock.get_requests(url=url)
        for item in source:
            if kind in {ObjectType.USER, ObjectType.PLAYLIST}:
                requests += spotify_mock.get_requests(url=f"{url}/{item["id"]}")
            if key:
                requests += spotify_mock.get_requests(url=f"{url}/{item["id"]}/{key}")
        self.assert_calls(expected=source, requests=requests, key=key, limit=limit, spotify_mock=spotify_mock)

        # test input maps are updated when API responses are given
        test = {id_: {k: v for k, v in item.items() if k not in update_keys} for id_, item in source_map.items()}
        for item in source:  # check source and test are different, skip comparing on 'kind_sub' key for performance
            source_no_items = {k: v for k, v in item.items() if k != key}
            assert {k: v for k, v in test[item["id"]].items() if k != key} != source_no_items

        results = api.get_items(values=test.values())
        self.assert_update(expected=source, results=results, test=test, kind=kind, key=key)

    ###########################################################################
    ## get_tracks_extra tests
    ###########################################################################
    def test_get_tracks_extra_single(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        source = choice(spotify_mock.tracks)
        source_features = spotify_mock.audio_features[source["id"]]
        source_analysis = spotify_mock.audio_analysis[source["id"]]
        test = random_id_type(id_=source["id"], wrangler=api, kind=ObjectType.TRACK)

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
        test = random_id_types(id_list=source_map, wrangler=api, kind=ObjectType.TRACK)

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

        test = random_id_type(id_=source["id"], wrangler=api, kind=ObjectType.TRACK)
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
