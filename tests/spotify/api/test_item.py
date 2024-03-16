from collections.abc import Collection
from copy import deepcopy
from itertools import batched
from random import sample, choice
from typing import Any
from urllib.parse import parse_qs

import pytest
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy as Request

from musify.shared.api.exception import APIError
from musify.shared.remote.enum import RemoteObjectType as ObjectType, RemoteIDType as IDType, RemoteIDType
from musify.shared.remote.exception import RemoteObjectTypeError
from musify.spotify.api import SpotifyAPI
from tests.shared.remote.utils import ALL_ITEM_TYPES
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.api.utils import get_limit, assert_calls
from tests.spotify.utils import random_ids, random_id, random_id_type, random_id_types
from tests.spotify.utils import random_uri, random_api_url, random_ext_url
from tests.utils import idfn, random_str


class TestSpotifyAPIItems:
    """Tester for item-type endpoints of :py:class:`SpotifyAPI`"""

    id_key = SpotifyAPI.id_key

    @pytest.fixture
    def responses(self, object_type: ObjectType, api_mock: SpotifyMock) -> dict[str, dict[str, Any]]:
        """Yields valid responses mapped by ID for a given ``object_type`` as a pytest.fixture"""
        api_mock.reset_mock()  # tests check the number of requests made
        source = api_mock.item_type_map[object_type]
        if len(source) > api_mock.limit_lower:
            source = sample(source, k=api_mock.limit_lower)

        return {response[self.id_key]: deepcopy(response) for response in source}

    @pytest.fixture
    def response(self, responses: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Yields a random valid response from a given set of ``responses`` as a pytest.fixture"""
        return choice(list(responses.values()))

    @pytest.fixture
    def extend(self, object_type: ObjectType, api: SpotifyAPI) -> bool:
        """For a given ``object_type``, should the API object attempt to extend the results"""
        return object_type in api.collection_item_map

    @pytest.fixture
    def key(self, object_type: ObjectType, extend: bool, api: SpotifyAPI) -> str:
        """For a given ``object_type``, determine the key of its sub objects if ``extend`` is True. None otherwise."""
        return api.collection_item_map[object_type].name.lower() + "s" if extend else None

    ###########################################################################
    ## Assertions
    ###########################################################################
    @staticmethod
    def assert_similar(source: dict[str, Any], *test: dict[str, Any], key: str | None = None):
        """Check ``source`` and ``test`` are the same, skip comparing on ``key`` for performance"""
        expected = {k: v for k, v in source.items() if k != key}
        for t in test:
            assert {k: v for k, v in t.items() if k != key} == expected

    @staticmethod
    def assert_differ(source: dict[str, Any], *test: dict[str, Any], key: str | None = None):
        """Check ``source`` and ``test`` are different, skip comparing on ``key`` for performance"""
        expected = {k: v for k, v in source.items() if k != key}
        for t in test:
            assert {k: v for k, v in t.items() if k != key} != expected

    @staticmethod
    def assert_params(requests: list[Request], params: dict[str, Any] | list[dict[str, Any]]):
        """Check for expected ``params`` in the given ``requests``"""
        for request in requests:
            request_params = parse_qs(request.query)
            if isinstance(params, list):
                assert any(request_params[k][0] == param[k] for param in params for k in param)
                continue

            for k, v in params.items():
                assert k in request_params
                assert request_params[k][0] == params[k]

    @staticmethod
    def assert_item_types(results: list[dict[str, Any]], key: str, object_type: ObjectType | None = None):
        """
        Assert all items are of the correct type by checking the result at key 'type' has value ``key``.
        Provide an ``object_type`` to apply object_type specific logic.
        """
        key = key.rstrip("s")
        for result in results:
            if object_type == ObjectType.PLAYLIST:
                # playlist responses next items deeper under 'track' key
                assert result[key]["type"] == key
            else:
                assert result["type"] == key

    def assert_get_items_results(
            self,
            results: list[dict[str, Any]],
            expected: dict[str, dict[str, Any]],
            test: dict[str, dict[str, Any]] | None = None,
            object_type: ObjectType | None = None,
            key: str | None = None,
    ):
        """
        Various assertions for get_items method results.

        - Assert the length of ``results`` and ``expected`` match
        - If ``key`` is not given, assume the given results relate to a collection and run assertions on its sub-items.
          If not given, just simply check each result is the same as its expected value.
        - If ``test`` is given, further assert the originally input ``test`` API response values
          were updated by the get_items operation.
        """
        assert len(results) == len(expected)

        for result in results:
            expect = expected[result[self.id_key]]
            if not key:  # get_items ran with no extension
                # no sub-items so responses are relatively small
                # we can therefore assert result == expected as it is a relatively quick comparison
                assert result == expect
                if test:
                    assert test[result[self.id_key]] == result
                continue

            # get_items ran and extended the initial results
            # just check length of sub-items match and objet_types are correct
            # fully checking result == expected would take too long as responses are normally very large

            similarity_test = [result]
            if test:
                assert len(test[result[self.id_key]][key]["items"]) == expect[key]["total"]
                similarity_test.append(test[result[self.id_key]])

            assert len(result[key]["items"]) == expect[key]["total"]
            self.assert_item_types(results=result[key]["items"], object_type=object_type, key=key)
            self.assert_similar(expect, result, *similarity_test, key=key)

    def assert_get_items_calls(
            self,
            responses: Collection[dict[str, Any]],
            object_type: ObjectType,
            api: SpotifyAPI,
            api_mock: SpotifyMock,
            key: str | None = None,
            limit: int | None = None,
    ):
        """Assert appropriate number of requests made for get_items method calls"""
        url = f"{api.url}/{object_type.name.lower()}s"
        requests = api_mock.get_requests(url=url)
        for response in responses:
            if limit is None or object_type in {ObjectType.USER, ObjectType.PLAYLIST}:
                requests += api_mock.get_requests(url=f"{url}/{response[self.id_key]}")
            if key:
                requests += api_mock.get_requests(url=f"{url}/{response[self.id_key]}/{key}")
        assert_calls(expected=responses, requests=requests, key=key, limit=limit, api_mock=api_mock)

    ###########################################################################
    ## Basic functionality
    ###########################################################################
    def test_get_unit(self, api: SpotifyAPI):
        assert api._get_unit() == api.items_key
        assert api._get_unit(key="track") == "tracks"
        assert api._get_unit(kind="Audio Features") == "audio features"
        assert api._get_unit(kind="Audio Features", key="tracks") == "audio features"
        assert api._get_unit(key="audio-features") == "audio features"

    def test_get_items_batches_limited(self, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        key = ObjectType.TRACK.name.lower() + "s"
        url = f"{api.url}/{key}"
        id_list = [track[self.id_key] for track in api_mock.tracks]
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
                api.get_user_items(user=random_str(1, RemoteIDType.ID.value - 1), kind=kind)

    def test_extend_tracks_input_validation(self, api: SpotifyAPI):
        assert api.extend_tracks(values=random_ids(), features=False, analysis=False) == []
        assert api.extend_tracks(values=[], features=True, analysis=True) == []

        value = api.wrangler.convert(random_id(), kind=ObjectType.ALBUM, type_in=IDType.ID, type_out=IDType.URL)
        with pytest.raises(RemoteObjectTypeError):
            api.extend_tracks(values=value, features=True)

    def test_get_artist_albums_input_validation(self, api: SpotifyAPI):
        assert api.get_artist_albums(values=[]) == {}

        value = api.wrangler.convert(random_id(), kind=ObjectType.ALBUM, type_in=IDType.ID, type_out=IDType.URL)
        with pytest.raises(RemoteObjectTypeError):
            api.get_artist_albums(values=value)

        with pytest.raises(APIError):
            api.get_artist_albums(values=random_id(), types=("unknown", "invalid"))

    ###########################################################################
    ## Multi-, Batched-, and Extend tests for each supported item type
    ###########################################################################
    def test_get_item_multi(
            self,
            object_type: ObjectType,
            responses: dict[str, dict[str, Any]],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        url = f"{api.url}/{object_type.name.lower()}s"
        params = {"key": "value"}

        results = api._get_items_multi(url=url, id_list=responses, params=params, key=None)
        requests = api_mock.get_requests(url=url)

        self.assert_item_types(results=results, key=object_type.name.lower())
        self.assert_get_items_results(results=results, expected=responses, object_type=object_type)
        self.assert_params(requests=requests, params=params)

        # appropriate number of requests were made for multi requests
        requests = [req for id_ in responses for req in api_mock.get_requests(url=f"{url}/{id_}")]
        assert len(requests) == len(responses)

    @pytest.mark.parametrize("object_type", [
        ObjectType.TRACK,
        ObjectType.ALBUM,
        ObjectType.ARTIST,
        ObjectType.SHOW,
        ObjectType.EPISODE,
        ObjectType.AUDIOBOOK,
        ObjectType.CHAPTER,
    ], ids=idfn)
    def test_get_item_batched(
            self,
            object_type: ObjectType,
            responses: dict[str, dict[str, Any]],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        key = object_type.name.lower() + "s"
        url = f"{api.url}/{key}"
        params = {"key": "value"}
        limit = get_limit(responses, max_limit=api_mock.limit_max, pages=3)

        results = api._get_items_batched(url=url, id_list=responses, params=params, key=key, limit=limit)
        requests = api_mock.get_requests(url=url)

        self.assert_item_types(results=results, key=object_type.name.lower())
        self.assert_get_items_results(results=results, expected=responses, object_type=object_type)
        self.assert_params(requests=requests, params=params)

        # appropriate number of requests were made for batched requests
        id_params = [{"ids": ",".join(ids)} for ids in batched(responses, limit)]
        requests = [req for req in requests if "ids" in parse_qs(req.query)]
        assert len(requests) == len(id_params) < len(results)
        self.assert_params(requests=requests, params=id_params)

    # TODO: add assertions/tests for RemoteResponses input
    @pytest.mark.parametrize("object_type", [
        ObjectType.PLAYLIST, ObjectType.ALBUM,  ObjectType.SHOW, ObjectType.AUDIOBOOK,
    ], ids=idfn)
    def test_extend_items(
            self,
            object_type: ObjectType,
            response: dict[str, Any],
            key: str,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        response = response[key]
        total = response["total"]
        limit = get_limit(total, max_limit=min(len(response[api.items_key]) // 3, api_mock.limit_max), pages=3)
        test = api_mock.format_items_block(
            url=response["href"], items=response[api.items_key][:limit], limit=limit, total=total
        )

        # assert ranges are valid for test to work and test value generated correctly
        assert len(response[api.items_key]) >= limit
        assert 0 < len(test[api.items_key]) <= limit
        assert response["total"] == test["total"]
        assert test["total"] > test["limit"]
        assert test["total"] > len(test[api.items_key])

        results = api.extend_items(response=test, key=api.collection_item_map.get(object_type, object_type))
        requests = api_mock.get_requests(url=response["href"].split("?")[0])

        # assert extension to total
        assert len(results) == total
        assert len(test[api.items_key]) == total
        assert test[api.items_key] == results  # extension happened to input value and results match input
        self.assert_item_types(results=test[api.items_key], object_type=object_type, key=key)

        # appropriate number of requests made (minus 1 for initial input)
        assert len(requests) == api_mock.calculate_pages(limit=limit, total=total) - 1

    ###########################################################################
    ## ``get_user_items``
    ###########################################################################
    @pytest.mark.parametrize("object_type,user", [
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
            self,
            object_type: ObjectType,
            user: bool,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        test = None
        if user:
            test = random_id_type(id_=api_mock.user_id, wrangler=api.wrangler, kind=ObjectType.USER)
            url = f"{api.url}/users/{api_mock.user_id}/{object_type.name.lower()}s"
        elif object_type == ObjectType.ARTIST:
            url = f"{api.url}/me/following"
        else:
            url = f"{api.url}/me/{object_type.name.lower()}s"

        responses = {
            response[self.id_key] if self.id_key in response else response[object_type.name.lower()][self.id_key]:
                deepcopy(response)
            for response in api_mock.item_type_map_user[object_type]
        }
        if object_type == ObjectType.PLAYLIST:  # ensure items block is reduced for playlist responses as expected
            for response in responses.values():
                response["tracks"] = {"href": response["tracks"]["href"], "total": response["tracks"]["total"]}

        total = len(responses)
        limit = get_limit(total, max_limit=api_mock.limit_max, pages=3)

        results = api.get_user_items(user=test, kind=object_type, limit=limit)
        assert len(results) == total

        # appropriate number of requests made
        requests = api_mock.get_requests(url=url)
        assert len(requests) == api_mock.calculate_pages(limit=limit, total=total)

        for result in results:  # check results are as expected
            if object_type not in {ObjectType.PLAYLIST, ObjectType.ARTIST}:
                assert "added_at" in result
                result = result[object_type.name.lower()]
                assert result == responses[result[self.id_key]][object_type.name.lower()]
            else:
                assert result == responses[result[self.id_key]]

    ###########################################################################
    ## ``get_items`` - tests
    ###########################################################################
    # TODO: add assertions/tests for RemoteResponses input

    update_keys = {
        ObjectType.PLAYLIST: {"description", "followers", "images", "public"},
        ObjectType.TRACK: {"artists", "album"},
        ObjectType.ALBUM: {"artists", "copyrights", "external_ids", "genres", "label", "popularity", "tracks"},
        ObjectType.ARTIST: {"followers", "genres", "images", "popularity"},
        ObjectType.USER: {"display_name", "followers", "images", "product"},
        ObjectType.SHOW: {"copyrights", "images", "languages", "episodes"},
        ObjectType.EPISODE: {"language", "images", "languages", "show"},
        ObjectType.AUDIOBOOK: {"copyrights", "edition", "languages", "images", "chapters"},
        ObjectType.CHAPTER: {"languages", "images", "chapters"},
    }

    def test_get_items_single_string(
            self,
            object_type: ObjectType,
            response: dict[str, Any],
            extend: bool,
            key: str,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        results = api.get_items(
            values=random_id_type(id_=response[self.id_key], wrangler=api.wrangler, kind=object_type),
            kind=object_type,
            extend=extend
        )
        self.assert_item_types(results=results, key=object_type.name.lower())
        self.assert_get_items_results(
            results=results, expected={response[self.id_key]: response}, object_type=object_type, key=key
        )
        self.assert_get_items_calls(responses=[response], object_type=object_type, key=key, api=api, api_mock=api_mock)

        # just check that these don't fail
        api.get_items(values=response["uri"])
        api.get_items(values=response["href"])
        api.get_items(values=response["external_urls"]["spotify"])

    def test_get_items_many_string(
            self,
            object_type: ObjectType,
            responses: dict[str, dict[str, Any]],
            extend: bool,
            key: str,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        limit = None
        if object_type not in {ObjectType.PLAYLIST, ObjectType.USER}:
            limit = get_limit(responses, max_limit=api_mock.limit_max)
            assert len(responses) > limit

        results = api.get_items(
            values=random_id_types(id_list=responses, wrangler=api.wrangler, kind=object_type),
            kind=object_type,
            limit=limit or api_mock.limit_max,
            extend=extend
        )
        self.assert_item_types(results=results, key=object_type.name.lower())
        self.assert_get_items_results(results=results, expected=responses, object_type=object_type, key=key)
        self.assert_get_items_calls(
            responses=responses.values(), object_type=object_type, key=key, limit=limit, api=api, api_mock=api_mock
        )

    def test_get_items_single_mapping(
            self,
            object_type: ObjectType,
            response: dict[str, Any],
            extend: bool,
            key: str,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        test = {k: v for k, v in response.items() if k not in self.update_keys[object_type]}
        self.assert_differ(response, test, key=key)

        results = api.get_items(values=test)
        self.assert_item_types(results=results, key=object_type.name.lower())
        self.assert_get_items_results(
            results=results,
            expected={response[self.id_key]: response},
            test={test[self.id_key]: test},
            key=key,
            object_type=object_type
        )

    def test_get_items_many_mapping(
            self,
            object_type: ObjectType,
            responses: dict[str, dict[str, Any]],
            extend: bool,
            key: str,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        # test input maps are updated when API responses are given
        test = {
            id_: {k: v for k, v in response.items() if k not in self.update_keys[object_type]}
            for id_, response in responses.items()
        }
        for response in responses.values():
            self.assert_differ(response, test[response[self.id_key]], key=key)

        results = api.get_items(values=test.values())
        self.assert_item_types(results=results, key=object_type.name.lower())
        self.assert_get_items_results(results=results, expected=responses, test=test, key=key, object_type=object_type)

    ###########################################################################
    ## ``extend_tracks`` tests
    ###########################################################################
    @pytest.fixture
    def features_all(self, responses: dict[str, dict[str, Any]], api_mock: SpotifyMock) -> dict[str, dict[str, Any]]:
        """Yield all audio features responses for the given ``responses`` as a pytest.fixture"""
        for response in responses:
            assert "audio_features" not in response
        return {id_: deepcopy(api_mock.audio_features[id_]) for id_ in responses}

    @pytest.fixture
    def features(self, response: dict[str, Any], features_all: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Yield the audio features  response for the given ``response`` as a pytest.fixture"""
        assert "audio_features" not in response
        return features_all[response[self.id_key]]

    @pytest.fixture
    def analysis_all(self, responses: dict[str, dict[str, Any]], api_mock: SpotifyMock) -> dict[str, dict[str, Any]]:
        """Yield all audio analyses responses for the given ``responses`` as a pytest.fixture"""
        for response in responses:
            assert "audio_analysis" not in response
        return {id_: deepcopy(api_mock.audio_analysis[id_]) for id_ in responses}

    @pytest.fixture
    def analysis(self, response: dict[str, Any], analysis_all: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Yield all audio analysis response for the given ``response`` as a pytest.fixture"""
        assert "audio_analysis" not in response
        return analysis_all[response[self.id_key]]

    def assert_extend_tracks_results(
            self,
            results: list[dict[str, Any]],
            test: dict[str, dict[str, Any]] | None = None,
            features: dict[str, dict[str, Any]] | None = None,
            features_updated: bool = True,
            analysis: dict[str, dict[str, Any]] | None = None,
            analysis_updated: bool = True,
    ):
        """
        Check the results contain the appropriate keys and values after running ``extend_tracks`` related methods.
        """
        if test:
            assert len(results) == len(test)

        for result in results:
            if features:
                expected = features[result[self.id_key]]
                if features_updated:
                    assert result["audio_features"] == expected
                else:
                    assert "audio_features" not in result

                if test:
                    assert test[result[self.id_key]]["audio_features"] == expected
            else:
                assert "audio_features" not in result
                if test:
                    assert "audio_features" not in test[result[self.id_key]]

            if analysis:
                expected = analysis[result[self.id_key]] | {self.id_key: result[self.id_key]}
                assert result["audio_analysis"] == expected
                if analysis_updated:
                    assert result["audio_analysis"] == expected
                else:
                    assert "audio_analysis" not in result

                if test:
                    assert test[result[self.id_key]]["audio_analysis"] == expected
            else:
                assert "audio_analysis" not in result
                if test:
                    assert "audio_analysis" not in test[result[self.id_key]]

    def assert_extend_tracks_calls(
            self,
            responses: Collection[dict[str, Any]],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
            features: bool = True,
            analysis: bool = True,
            limit: int = 1,
    ):
        """Assert appropriate number of requests made for extend_tracks method calls"""
        requests = []
        if features and limit > 1:
            requests += api_mock.get_requests(url=f"{api.url}/audio-features")
        if analysis and limit > 1:
            requests += api_mock.get_requests(url=f"{api.url}/audio-analysis")

        for response in responses:
            if features:
                requests += api_mock.get_requests(url=f"{api.url}/audio-features/{response[self.id_key]}")
            if analysis:
                requests += api_mock.get_requests(url=f"{api.url}/audio-analysis/{response[self.id_key]}")

        assert len(api_mock.request_history) == len(list(batched(responses, limit))) + len(responses)

    # TODO: add assertions/tests for RemoteResponses input
    @pytest.mark.parametrize("object_type", [ObjectType.TRACK], ids=idfn)
    def test_extend_tracks_single_string(
            self,
            object_type: ObjectType,
            response: dict[str, Any],
            features: dict[str, Any],
            analysis: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        results = api.extend_tracks(
            values=random_id_type(id_=response[self.id_key], wrangler=api.wrangler, kind=ObjectType.TRACK),
            features=True,
            analysis=True
        )

        assert len(results) == 1
        self.assert_extend_tracks_results(
            results=results, features={response[self.id_key]: features}, analysis={response[self.id_key]: analysis}
        )
        self.assert_extend_tracks_calls(
            responses=[response], features=True, analysis=True, api=api, api_mock=api_mock
        )

        # just check that these don't fail
        api.extend_tracks(values=response["uri"])
        api.extend_tracks(values=response["href"])
        api.extend_tracks(values=response["external_urls"]["spotify"])

    @pytest.mark.parametrize("object_type", [ObjectType.TRACK], ids=idfn)
    def test_extend_tracks_single_mapping(
            self,
            object_type: ObjectType,
            response: dict[str, Any],
            features: dict[str, Any],
            analysis: dict[str, Any],
            api: SpotifyAPI,
    ):
        results = api.extend_tracks(values=response, features=True, analysis=False)
        self.assert_extend_tracks_results(
            results=results, test={response[self.id_key]: response}, features={response[self.id_key]: features},
        )

        results = api.extend_tracks(values=response, features=False, analysis=True)
        self.assert_extend_tracks_results(
            results=results,
            test={response[self.id_key]: response},
            features={response[self.id_key]: features},
            features_updated=False,
            analysis={response[self.id_key]: analysis},
        )

    @pytest.mark.parametrize("object_type", [ObjectType.TRACK], ids=idfn)
    def test_extend_tracks_many_string(
            self,
            object_type: ObjectType,
            responses: dict[str, Any],
            features_all: dict[str, dict[str, Any]],
            analysis_all: dict[str, dict[str, Any]],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
    ):
        limit = get_limit(responses, max_limit=api_mock.limit_max)
        test = random_id_types(id_list=responses, wrangler=api.wrangler, kind=ObjectType.TRACK)

        results = api.extend_tracks(values=test, features=True, analysis=True, limit=limit)

        self.assert_extend_tracks_results(results=results, features=features_all, analysis=analysis_all)
        self.assert_extend_tracks_calls(
            responses=responses.values(), features=True, analysis=True, api=api, api_mock=api_mock, limit=limit
        )

    # noinspection PyTestUnpassedFixture
    @pytest.mark.parametrize("object_type", [ObjectType.TRACK], ids=idfn)
    def test_extend_tracks_many_mapping(
            self,
            object_type: ObjectType,
            responses: dict[str, Any],
            features_all: dict[str, dict[str, Any]],
            analysis_all: dict[str, dict[str, Any]],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
    ):
        results = api.extend_tracks(values=responses.values(), features=True, analysis=False)
        self.assert_extend_tracks_results(results=results, test=responses, features=features_all,)

        results = api.extend_tracks(values=responses.values(), features=False, analysis=True)
        self.assert_extend_tracks_results(
            results=results, test=responses, features=features_all, features_updated=False, analysis=analysis_all,
        )

    # TODO: add assertions/tests for RemoteResponses input
    @pytest.mark.parametrize("object_type", [ObjectType.TRACK], ids=idfn)
    def test_get_tracks(
            self,
            object_type: ObjectType,
            response: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
    ):
        results = api.get_tracks(
            values=random_id_type(id_=response[self.id_key], wrangler=api.wrangler, kind=ObjectType.TRACK),
            features=True,
            analysis=True
        )
        assert {k: v for k, v in results[0].items() if k not in {"audio_features", "audio_analysis"}} == response
        assert "audio_features" not in response
        assert "audio_analysis" not in response

        results = api.get_tracks(values=response, features=True, analysis=True)
        assert results[0] == response
        assert "audio_features" in response
        assert "audio_analysis" in response
