from collections.abc import Collection
from copy import deepcopy
from itertools import batched
from random import sample, choice
from typing import Any
from urllib.parse import parse_qs

import pytest
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy as Request

from syncify.api.exception import APIError
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

    @staticmethod
    def assert_calls(
            expected: Collection[dict[str, Any]],
            requests: list[Request],
            api_mock: SpotifyMock,
            key: str | None = None,
            limit: int | None = None,
    ):
        """Assert an appropriate number of calls were made for multi- or batch- call functions"""
        # assume at least 1 call was made in the case where call returned 0 results i.e. len(expected) == 0
        initial_calls = max(len(list(batched(expected, limit))) if limit else len(expected), 1)
        extend_calls = 0
        if key:
            # minus 1 for initial call to get the collection
            extend_calls += sum(api_mock.calculate_pages_from_response(expect) - 1 for expect in expected)

        assert len(requests) == initial_calls + extend_calls

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    def test_get_unit(self, api: SpotifyAPI):
        assert api._get_unit() == api.items_key
        assert api._get_unit(key="track") == "tracks"
        assert api._get_unit(unit="Audio Features") == "audio features"
        assert api._get_unit(unit="Audio Features", key="tracks") == "audio features"
        assert api._get_unit(key="audio-features") == "audio features"

    def test_get_items_batches_limited(self, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        key = ObjectType.TRACK.name.casefold() + "s"
        url = f"{api.api_url_base}/{key}"
        id_list = [track["id"] for track in api_mock.tracks]
        valid_limit = 30

        api._get_items_batched(url=url, id_list=sample(id_list, k=api_mock.limit_lower), key=key, limit=-30)
        api._get_items_batched(url=url, id_list=id_list, key=key, limit=200)
        api._get_items_batched(url=url, id_list=id_list, key=key, limit=valid_limit)

        for request in api_mock.get_requests(url=url):
            request_params = parse_qs(request.query)
            count = len(request_params["ids"][0].split(","))
            assert count >= 1
            assert count <= api_mock.limit_max

    ###########################################################################
    ## Input validation
    ###########################################################################
    def test_get_items_input_validation(self, api: SpotifyAPI):
        assert api.get_items(values=[]) == []

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

    def test_get_artist_albums_input_validation(self, api: SpotifyAPI):
        assert api.get_artist_albums(values=[]) == {}

        value = api.convert(random_id(), kind=ObjectType.ALBUM, type_in=IDType.ID, type_out=IDType.URL)
        with pytest.raises(RemoteObjectTypeError):
            api.get_artist_albums(values=value)

        with pytest.raises(APIError):
            api.get_artist_albums(values=random_id(), types=("unknown", "invalid"))

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

    @pytest.mark.parametrize("kind", [
        ObjectType.PLAYLIST,
        ObjectType.TRACK,
        ObjectType.ALBUM,
        ObjectType.ARTIST,
        ObjectType.USER,
        ObjectType.SHOW,
        ObjectType.EPISODE,
        ObjectType.AUDIOBOOK,
        ObjectType.CHAPTER,
    ], ids=idfn)
    def test_get_item_multi(self, kind: ObjectType, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        params = {"key": "value"}

        source = api_mock.item_type_map[kind]
        source = sample(source, k=api_mock.limit_lower) if len(source) > api_mock.limit_lower else source
        source_map = {item["id"]: item for item in source}
        id_list = [item["id"] for item in source]

        results = api._get_items_multi(url=url, id_list=id_list, params=params, key=None)
        requests = api_mock.get_requests(url=url)

        self.assert_get_items_results(expected=source_map, results=results, kind=kind)
        self.assert_params(requests=requests, params=params)
        # appropriate number of requests were made for multi requests
        assert sum(len(api_mock.get_requests(url=f"{url}/{id_}")) for id_ in id_list) == len(source)

    @pytest.mark.parametrize("kind", [
        ObjectType.TRACK,
        ObjectType.ALBUM,
        ObjectType.ARTIST,
        ObjectType.SHOW,
        ObjectType.EPISODE,
        ObjectType.AUDIOBOOK,
        ObjectType.CHAPTER,
    ], ids=idfn)
    def test_get_item_batched(self, kind: ObjectType, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        key = kind.name.casefold() + "s"
        url = f"{api.api_url_base}/{key}"
        params = {"key": "value"}

        source = api_mock.item_type_map[kind]
        source_map = {item["id"]: item for item in source}
        id_list = [item["id"] for item in source]
        limit = min(len(source) // 3, api_mock.limit_max)  # force pagination
        assert len(source) > limit  # ensure ranges are valid for test to work

        results = api._get_items_batched(url=url, id_list=id_list, params=params, key=key, limit=limit)
        requests = api_mock.get_requests(url=url)

        self.assert_get_items_results(expected=source_map, results=results, kind=kind)
        self.assert_params(requests=requests, params=params)

        # appropriate number of requests were made for batched requests
        id_params = [{"ids": ",".join(ids)} for ids in batched(id_list, limit)]
        requests = [req for req in requests if "ids" in parse_qs(req.query)]
        assert len(requests) == len(id_params)
        self.assert_params(requests=requests, params=id_params)

    @pytest.mark.parametrize("kind", [
        ObjectType.PLAYLIST, ObjectType.ALBUM,  ObjectType.SHOW, ObjectType.AUDIOBOOK,
    ], ids=idfn)
    def test_extend_items(self, kind: ObjectType, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        key = api.collection_item_map.get(kind, kind).name.casefold() + "s"
        source = deepcopy(next(item[key] for item in api_mock.item_type_map[kind] if item[key]["total"] >= 4))
        total = source["total"]
        limit = max(min(total // 3, len(source[api.items_key]) // 3, api_mock.limit_max), 1)  # force pagination
        items = source[api.items_key][:limit]

        test = api_mock.format_items_block(url=source["href"], items=items, limit=limit, total=total)

        # assert ranges are valid for test to work and test value generated correctly
        assert len(source[api.items_key]) >= limit
        assert 0 < len(items) <= limit
        assert source["total"] == test["total"]
        assert test["total"] > test["limit"]
        assert test["total"] > len(test[api.items_key])

        results = api.extend_items(items_block=test, key=key)
        requests = api_mock.get_requests(url=source["href"].split("?")[0])

        # assert extension to total
        assert len(results) == total
        assert len(test[api.items_key]) == total
        assert test[api.items_key] == results  # extension happened to input value and results match input
        self.assert_item_types(results=test[api.items_key], kind=kind, key=key)

        # appropriate number of requests made (minus 1 for initial input)

        assert len(requests) == api_mock.calculate_pages(limit=limit, total=total) - 1

    ###########################################################################
    ## ``get_user_items``
    ###########################################################################
    @pytest.mark.parametrize("kind,user", [
        (ObjectType.PLAYLIST, False),
        (ObjectType.PLAYLIST, True),
        (ObjectType.TRACK, False),
        (ObjectType.ALBUM, False),
        (ObjectType.ARTIST, False),
        (ObjectType.SHOW, False),
        (ObjectType.EPISODE, False),
        (ObjectType.AUDIOBOOK, False),
    ], ids=idfn)
    def test_get_user_items(
            self, kind: ObjectType, user: bool, api: SpotifyAPI, api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        test = None
        if user:
            test = random_id_type(id_=api_mock.user_id, wrangler=api, kind=ObjectType.USER)
            url = f"{api.api_url_base}/users/{api_mock.user_id}/{kind.name.casefold()}s"
        elif kind == ObjectType.ARTIST:
            url = f"{api.api_url_base}/me/following"
        else:
            url = f"{api.api_url_base}/me/{kind.name.casefold()}s"

        source = deepcopy(api_mock.item_type_map_user[kind])
        if kind == ObjectType.PLAYLIST:  # ensure items block is reduced for playlist responses as expected
            for pl in source:
                pl["tracks"] = {"href": pl["tracks"]["href"], "total": pl["tracks"]["total"]}

        source_map = {item["id"] if "id" in item else item[kind.name.casefold()]["id"]: item for item in source}

        total = len(source)
        limit = max(min(total // 3, api_mock.limit_max), 1)  # force pagination
        assert total > limit  # ensure ranges are valid for test to work

        results = api.get_user_items(user=test, kind=kind, limit=limit)
        assert len(results) == total

        # appropriate number of requests made
        requests = [req for req in api_mock.get_requests(url=url)]
        assert len(requests) == api_mock.calculate_pages(limit=limit, total=total)

        for result in results:  # check results are as expected
            if kind not in {ObjectType.PLAYLIST, ObjectType.ARTIST}:
                assert "added_at" in result
                result = result[kind.name.casefold()]
                assert result == source_map[result["id"]][kind.name.casefold()]
            else:
                assert result == source_map[result["id"]]

    ###########################################################################
    ## ``get_items`` - assertions
    ###########################################################################
    def assert_get_items_results(
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
    def assert_get_items_update(
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
    ## ``get_items`` - tests
    ###########################################################################
    @pytest.mark.parametrize("kind,update_keys", [
        (ObjectType.PLAYLIST, {"description", "followers", "images", "public"}),
        (ObjectType.TRACK, {"artists", "album"}),
        (ObjectType.ALBUM, {"artists", "copyrights", "external_ids", "genres", "label", "popularity", "tracks"}),
        (ObjectType.ARTIST, {"followers", "genres", "images", "popularity"}),
        (ObjectType.USER, {"display_name", "followers", "images", "product"}),
        (ObjectType.SHOW, {"copyrights", "images", "languages", "episodes"}),
        (ObjectType.EPISODE, {"language", "images", "languages", "show"}),
        (ObjectType.AUDIOBOOK, {"copyrights", "edition", "languages", "images", "chapters"}),
        (ObjectType.CHAPTER, {"languages", "images", "chapters"}),
    ], ids=idfn)
    def test_get_items_single(
            self, kind: ObjectType, update_keys: set[str], api: SpotifyAPI, api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        extend = kind in api.collection_item_map
        key = api.collection_item_map[kind].name.casefold() + "s" if extend else None

        source = deepcopy(choice(api_mock.item_type_map[kind]))
        test = random_id_type(id_=source["id"], wrangler=api, kind=kind)

        results = api.get_items(values=test, kind=kind, extend=extend)
        self.assert_get_items_results(expected={source["id"]: source}, results=results, kind=kind, key=key)

        # appropriate number of requests made
        url = f"{api.api_url_base}/{kind.name.casefold()}s/{source["id"]}"
        requests = api_mock.get_requests(url=url)
        if key:
            requests += api_mock.get_requests(url=f"{url}/{key}")
        self.assert_calls(expected=[source], requests=requests, key=key, limit=None, api_mock=api_mock)

        # test input map is updated when API response is given
        test = {k: v for k, v in source.items() if k not in update_keys}
        # check source and test are different, skip comparing on 'kind_sub' key for performance
        expected_no_items = {k: v for k, v in source.items() if k != key}
        assert {k: v for k, v in test.items() if k != key} != expected_no_items

        results = api.get_items(values=test)
        self.assert_get_items_update(expected=[source], results=results, test={test["id"]: test}, kind=kind, key=key)

        # just check that these don't fail
        api.get_items(values=source["uri"])
        api.get_items(values=source["href"])
        api.get_items(values=source["external_urls"]["spotify"])

    @pytest.mark.parametrize("kind,update_keys", [
        (ObjectType.PLAYLIST, {"description", "followers", "images", "public"}),
        (ObjectType.TRACK, {"artists", "album"}),
        (ObjectType.ALBUM, {"artists", "copyrights", "external_ids", "genres", "label", "popularity", "tracks"}),
        (ObjectType.ARTIST, {"followers", "genres", "images", "popularity"}),
        (ObjectType.USER, {"display_name", "followers", "images", "product"}),
        (ObjectType.SHOW, {"copyrights", "images", "languages", "episodes"}),
        (ObjectType.EPISODE, {"language", "images", "languages", "show"}),
        (ObjectType.AUDIOBOOK, {"copyrights", "edition", "languages", "images", "chapters"}),
        (ObjectType.CHAPTER, {"languages", "images", "chapters"}),
    ], ids=idfn)
    def test_get_items_many(
            self, kind: ObjectType, update_keys: set[str], api: SpotifyAPI, api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        extend = kind in api.collection_item_map
        key = api.collection_item_map[kind].name.casefold() + "s" if extend else None

        source = api_mock.item_type_map[kind]
        source = sample(source, api_mock.limit_lower) if len(source) > api_mock.limit_lower else source
        source_map = {item["id"]: deepcopy(item) for item in source}
        test = random_id_types(id_list=source_map, wrangler=api, kind=kind)

        # force pagination
        limit = max(min(len(source) // 3, api_mock.limit_max), 1)
        limit = limit if kind not in {ObjectType.PLAYLIST, ObjectType.USER} else None
        if limit is not None:  # ensure ranges are valid for test to work
            assert len(source) > limit

        results = api.get_items(values=test, kind=kind, limit=limit or api_mock.limit_max, extend=extend)
        self.assert_get_items_results(expected=source_map, results=results, kind=kind, key=key)

        # appropriate number of requests made
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        requests = api_mock.get_requests(url=url)
        for item in source:
            if kind in {ObjectType.USER, ObjectType.PLAYLIST}:
                requests += api_mock.get_requests(url=f"{url}/{item["id"]}")
            if key:
                requests += api_mock.get_requests(url=f"{url}/{item["id"]}/{key}")
        self.assert_calls(expected=source, requests=requests, key=key, limit=limit, api_mock=api_mock)

        # test input maps are updated when API responses are given
        test = {id_: {k: v for k, v in item.items() if k not in update_keys} for id_, item in source_map.items()}
        for item in source:  # check source and test are different, skip comparing on 'kind_sub' key for performance
            source_no_items = {k: v for k, v in item.items() if k != key}
            assert {k: v for k, v in test[item["id"]].items() if k != key} != source_no_items

        results = api.get_items(values=test.values())
        self.assert_get_items_update(expected=source, results=results, test=test, kind=kind, key=key)

    ###########################################################################
    ## ``get_tracks_extra`` tests
    ###########################################################################
    def test_get_tracks_extra_single(self, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        source = deepcopy(choice(api_mock.tracks))
        source_features = api_mock.audio_features[source["id"]]
        source_analysis = api_mock.audio_analysis[source["id"]]
        test = random_id_type(id_=source["id"], wrangler=api, kind=ObjectType.TRACK)

        results = api.get_tracks_extra(values=test, features=True, analysis=True)
        assert set(results) == {"audio_features", "audio_analysis"}
        assert results["audio_features"][0] == source_features
        assert results["audio_analysis"][0] == source_analysis | {"id": source["id"]}

        # appropriate number of requests made
        requests = api_mock.get_requests(url=f"{api.api_url_base}/audio-features/{source["id"]}")
        requests += api_mock.get_requests(url=f"{api.api_url_base}/audio-analysis/{source["id"]}")
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
        assert test["audio_analysis"] == source_analysis | {"id": source["id"]}

        # just check that these don't fail
        api.get_tracks_extra(values=source["uri"])
        api.get_tracks_extra(values=source["href"])
        api.get_tracks_extra(values=source["external_urls"]["spotify"])

    def test_get_tracks_extra_many(self, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        source = api_mock.tracks
        source = sample(source, api_mock.limit_lower) if len(source) > api_mock.limit_lower else source
        source_map = {item["id"]: deepcopy(item) for item in source}
        source_features = {item["id"]: api_mock.audio_features[item["id"]] for item in source}
        source_analysis = {item["id"]: api_mock.audio_analysis[item["id"]] for item in source}
        test = random_id_types(id_list=source_map, wrangler=api, kind=ObjectType.TRACK)

        limit = max(min(len(source) // 3, api_mock.limit_max), 1)  # force pagination
        assert len(source) > limit  # ensure ranges are valid for test to work

        results = api.get_tracks_extra(values=test, features=True, analysis=True, limit=limit)

        assert set(results) == {"audio_features", "audio_analysis"}
        for result in results["audio_features"]:
            assert result == source_features[result["id"]]
        for result, expected in zip(results["audio_analysis"], source_analysis.values()):
            assert result == expected | {"id": result["id"]}

        # appropriate number of requests made
        requests = api_mock.get_requests(url=f"{api.api_url_base}/audio-features")
        for id_ in source_map:
            requests += api_mock.get_requests(url=f"{api.api_url_base}/audio-analysis/{id_}")
        assert len(api_mock.request_history) == len(list(batched(test, limit))) + len(test)

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
            assert item["audio_analysis"] == source_analysis[id_] | {"id": item["id"]}

    def test_get_tracks(self, api: SpotifyAPI, api_mock: SpotifyMock):
        source = choice(api_mock.tracks)

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

    ###########################################################################
    ## ``get_artist_albums`` tests
    ###########################################################################
    @staticmethod
    def assert_artist_albums_enriched(albums: list[dict[str, Any]]) -> None:
        for album in albums:
            assert "tracks" in album
            assert album["tracks"]["total"] == album["total_tracks"]
            assert album["id"] in album["tracks"]["href"]

    def assert_artist_albums_results(
            self,
            results: dict[str, list[dict[str, Any]]],
            source: dict[str, dict[str, Any]],
            expected: dict[str, list[dict[str, Any]]],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
            limit: int,
            update: bool,
    ):
        assert len(results) == len(expected)

        for id_, result in results.items():
            assert [{k: v for k, v in r.items() if k != "tracks"} for r in result] == expected[id_]
            self.assert_artist_albums_enriched(result)

            # appropriate number of requests made
            url = f"{api.api_url_base}/artists/{id_}/albums"
            requests = api_mock.get_requests(url=url)
            self.assert_calls(expected=expected[id_], requests=requests, limit=limit, api_mock=api_mock)

            if not update:
                assert "albums" not in source[id_]
                return

            assert len(source[id_]["albums"]["items"]) == source[id_]["albums"]["total"] == len(expected[id_])
            reduced = [{k: v for k, v in album.items() if k != "tracks"} for album in source[id_]["albums"]["items"]]
            assert reduced == expected[id_]
            self.assert_artist_albums_enriched(source[id_]["albums"]["items"])

    def test_get_artist_albums_single(self, api: SpotifyAPI, api_mock: SpotifyMock):
        types = ("album", "single")
        expected_map = {
            artist["id"]: [
                album for album in api_mock.artist_albums
                if any(art["id"] == artist["id"] for art in album["artists"])
                and album["album_type"] in types
            ]
            for artist in api_mock.artists
        }
        id_, expected = next((id_, albums) for id_, albums in expected_map.items() if len(albums) >= 10)
        source = deepcopy(next(artist for artist in api_mock.artists if artist["id"] == id_))
        test = random_id_type(id_=id_, wrangler=api, kind=ObjectType.ARTIST)

        # force pagination
        limit = max(min(len(expected) // 3, api_mock.limit_max), 1)
        assert len(expected) > limit  # ensure ranges are valid for test to work

        # string given
        api_mock.reset_mock()  # test checks the number of requests made
        self.assert_artist_albums_results(
            results=api.get_artist_albums(values=test, types=types, limit=limit),
            source={source["id"]: source},
            expected={source["id"]: expected},
            api=api,
            api_mock=api_mock,
            limit=limit,
            update=False
        )

        # API response given
        api_mock.reset_mock()  # test checks the number of requests made
        self.assert_artist_albums_results(
            results=api.get_artist_albums(values=source, types=types, limit=limit),
            source={source["id"]: source},
            expected={source["id"]: expected},
            api=api,
            api_mock=api_mock,
            limit=limit,
            update=True
        )

    def test_get_artist_albums_many(self, api: SpotifyAPI, api_mock: SpotifyMock):
        source = api_mock.artists
        source = sample(source, api_mock.limit_lower) if len(source) > api_mock.limit_lower else source
        source_map = {item["id"]: deepcopy(item) for item in source}
        expected_map = {
            id_: [album for album in api_mock.artist_albums if any(art["id"] == id_ for art in album["artists"])]
            for id_ in source_map
        }
        test = random_id_types(id_list=source_map, wrangler=api, kind=ObjectType.ARTIST)
        limit = 50

        # string given
        api_mock.reset_mock()  # test checks the number of requests made
        self.assert_artist_albums_results(
            results=api.get_artist_albums(values=test, limit=limit),
            source=source_map,
            expected=expected_map,
            api=api,
            api_mock=api_mock,
            limit=limit,
            update=False
        )

        # API response given
        api_mock.reset_mock()  # test checks the number of requests made
        self.assert_artist_albums_results(
            results=api.get_artist_albums(values=source_map.values(), limit=limit),
            source=source_map,
            expected=expected_map,
            api=api,
            api_mock=api_mock,
            limit=limit,
            update=True
        )
