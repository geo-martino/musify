import re
from collections.abc import Callable
from functools import partial
from random import randrange
from typing import Any
from urllib.parse import urlparse, parse_qs

import pytest
from requests_mock.mocker import Mocker
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember
from requests_mock.response import _Context as Context

from syncify.remote.enums import RemoteItemType, RemoteIDType
from syncify.remote.exception import RemoteItemTypeError
from syncify.spotify.api import SpotifyAPI
from tests.spotify.api.utils import SpotifyTestResponses as Responses, assert_limit_parameter_valid, random_id_type, \
    random_id_types, ALL_ITEM_TYPES
from tests.spotify.utils import random_ids, random_uri, random_api_url, random_ext_url
from tests.utils import random_str, random_dt


class TestSpotifyAPICollections:
    """Tester for collection-type endpoints of :py:class:`SpotifyAPI`"""

    supported_collections = {RemoteItemType.PLAYLIST, RemoteItemType.ALBUM}

    @staticmethod
    def get_items_block_json_response(
            req: Request, _: Context, kind: RemoteItemType, total: int, user_id: str | None = None
    ) -> dict[str, Any]:
        """Dynamically generate expected response for items block"""
        req_params = parse_qs(urlparse(req.url).query)
        limit = int(req_params["limit"][0])
        offset = int(req_params.get("offset", [0])[0])
        count = min(limit, total - offset)

        if kind == RemoteItemType.PLAYLIST:
            items = [Responses.playlist(user_id=user_id, tracks=False) for _ in range(count)]
        elif kind == RemoteItemType.ALBUM:
            items = [Responses.album(extend=True, artists=True, tracks=True) for _ in range(count)]
            for item in items:
                item["added_at"] = random_dt().strftime("%Y-%m-%dT%H:%M:%SZ")
        elif kind == RemoteItemType.TRACK:
            items = [Responses.track(album=True, artists=True) for _ in range(count)]
            for item in items:
                item["added_at"] = random_dt().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            raise Exception(f"RemoteItemType test not implemented: {kind.name}")

        return Responses.format_items_block(url=req.url, items=items, offset=offset, limit=limit, total=total)

    @staticmethod
    def assert_results_enriched(results: list[dict[str, Any]], kind: RemoteItemType) -> None:
        """Check a result has been enriched as expected"""
        for result in results:
            assert result["type"] == kind.name.casefold()

    ###########################################################################
    ## Basic functionality
    ###########################################################################

    ###########################################################################
    ## Extend item block tests
    ###########################################################################
    # TODO: expand to test for all possible RemoteItemTypes
    @pytest.mark.parametrize("kind,item_getter", [
        (RemoteItemType.PLAYLIST, partial(Responses.playlist, tracks=False)),
        (RemoteItemType.ALBUM, partial(Responses.album, extend=True, artists=True, tracks=True)),
        # (RemoteItemType.AUDIOBOOK, partial()),
        # (RemoteItemType.SHOW, partial()),
    ])
    def test_extend_items(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            item_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker
    ):
        """Run tests on extend item block function"""
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        initial = [item_getter() for _ in range(randrange(10, 20))]
        total = randrange(30, 60) + len(initial)
        initial_block = Responses.format_items_block(url=url, items=initial, offset=0, limit=len(initial), total=total)

        response_getter = partial(self.get_items_block_json_response, kind=kind, total=total)
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)

        results = api._extend_items(items_block=initial_block, kind=kind)

        assert len(results) == total
        assert len(initial_block[api.items_key]) == total
        assert initial_block[api.items_key] == results
        for item in initial_block[api.items_key]:
            assert item["type"] == kind.name.lower()

    ###########################################################################
    ## Get user collections
    ###########################################################################
    @staticmethod
    def test_get_collections_user_input_validation(api: SpotifyAPI):
        for kind in ALL_ITEM_TYPES:
            if kind in api.collection_item_map and kind != RemoteItemType.PLAYLIST:
                with pytest.raises(RemoteItemTypeError):
                    api.get_collections_user(user=random_str(10, RemoteIDType.ID.value - 1), kind=kind)
            elif kind in {RemoteItemType.TRACK, RemoteItemType.EPISODE}:
                with pytest.raises(RemoteItemTypeError):
                    api.get_collections_user(user=random_str(10, RemoteIDType.ID.value - 1), kind=kind)

            if kind not in api.collection_item_map and kind not in {RemoteItemType.TRACK, RemoteItemType.EPISODE}:
                with pytest.raises(RemoteItemTypeError):
                    api.get_collections_user(kind=kind)

    def test_get_collections_user_params_limited(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.PLAYLIST
        url = f"{api.api_url_base}/me/{kind.name.casefold()}s"
        
        response_getter = partial(self.get_items_block_json_response, kind=kind, total=15)
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)
        
        assert_limit_parameter_valid(
            test_function=partial(api.get_collections_user, kind=kind),
            requests_mock=requests_mock,
        )

    # TODO: expand to test for all possible RemoteItemTypes
    @pytest.mark.parametrize("kind,user_id", [
        (RemoteItemType.PLAYLIST, None),
        (RemoteItemType.PLAYLIST, random_str(20, 40)),
        (RemoteItemType.ALBUM, None),
        # (RemoteItemType.AUDIOBOOK, None),
        # (RemoteItemType.SHOW, None),
        (RemoteItemType.TRACK, None),
        # (RemoteItemType.EPISODE, None),
    ])
    def test_get_collections_user(
            self, api: SpotifyAPI, kind: RemoteItemType, user_id: str | None, requests_mock: Mocker
    ):
        if user_id:
            url = f"{api.api_url_base}/users/{user_id}/{kind.name.casefold()}s"
            user = random_id_type(id_=user_id, api=api, kind=RemoteItemType.USER)
        else:
            url = f"{api.api_url_base}/me/{kind.name.casefold()}s"
            user = None

        total = randrange(20, 30)
        limit = total // 4

        response_getter = partial(self.get_items_block_json_response, kind=kind, total=total)
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)

        results = api.get_collections_user(user=user, kind=kind, limit=limit)

        assert len(results) == total
        assert len(requests_mock.request_history) == (total // limit) + 1
        self.assert_results_enriched(results=results, kind=kind)

    ###########################################################################
    ## Get collections
    ###########################################################################
    def test_get_collections_input_validation(self, api: SpotifyAPI, requests_mock: Mocker):
        with pytest.raises(RemoteItemTypeError):
            api.get_collections(values=random_ids(), kind=None)

        with pytest.raises(RemoteItemTypeError):
            api.get_collections(values=random_uri(kind=RemoteItemType.TRACK), kind=RemoteItemType.SHOW)
        with pytest.raises(RemoteItemTypeError):
            api.get_collections(values=random_api_url(kind=RemoteItemType.ARTIST), kind=RemoteItemType.PLAYLIST)
        with pytest.raises(RemoteItemTypeError):
            api.get_collections(values=random_ext_url(kind=RemoteItemType.CHAPTER), kind=RemoteItemType.AUDIOBOOK)

        for kind in ALL_ITEM_TYPES:
            if kind in api.collection_item_map:
                continue

            with pytest.raises(RemoteItemTypeError):
                api.get_collections(values=random_ids(), kind=kind)

        kind = RemoteItemType.PLAYLIST
        url = f"{api.api_url_base}/me/{kind.name.casefold()}s"

        response_getter = partial(self.get_items_block_json_response, kind=kind, total=5)
        requests_mock.get(url=url, json=Responses.playlist(tracks=True))
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)

        with pytest.raises(RemoteItemTypeError):
            api.get_collections(values="does not exist", kind=kind)

    def test_get_collections_params_limited(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.PLAYLIST
        url = f"{api.api_url_base}/me/{kind.name.casefold()}s"

        response_getter = partial(self.get_items_block_json_response, kind=kind, total=15)
        requests_mock.get(url=re.compile(url + r"\?"), json=response_getter)

        assert_limit_parameter_valid(
            test_function=partial(api.get_collections_user, kind=kind),
            requests_mock=requests_mock,
        )

    # TODO: expand to test for all possible RemoteItemTypes
    @pytest.mark.parametrize("kind,collection_getter", [
        (RemoteItemType.PLAYLIST, partial(Responses.playlist, tracks=True)),
        (RemoteItemType.ALBUM, partial(Responses.album, extend=True, artists=True, tracks=True)),
        # (RemoteItemType.AUDIOBOOK, partial()),
        # (RemoteItemType.SHOW, partial()),
    ])
    def test_get_collections_on_single_string(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            collection_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker
    ):
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        items_key = api.collection_item_map[kind].name.casefold() + "s"

        collection_initial = collection_getter()
        collection_test = random_id_type(id_=collection_initial["id"], api=api, kind=kind)

        limit = collection_initial[items_key]["limit"]
        total = collection_initial[items_key]["total"]

        response_getter = partial(self.get_items_block_json_response, kind=kind, total=total)
        requests_mock.get(url=f"{url}/{collection_initial["id"]}", json=collection_initial)
        requests_mock.get(url=re.compile(rf"{url}/{collection_initial["id"]}\?"), json=response_getter)

        results = api.get_collections(values=collection_test, kind=kind)

        assert len(results) == 1
        assert len(requests_mock.request_history) == (total // limit) + 1
        self.assert_results_enriched(results=results, kind=kind)

        # just check that these don't fail
        requests_mock.get(url=re.compile(url), json=collection_initial)
        requests_mock.get(url=re.compile(rf"{url}/.*\?"), json=response_getter)
        api.get_collections(values=random_uri(kind=kind))
        api.get_collections(values=random_api_url(kind=kind))
        api.get_collections(values=random_ext_url(kind=kind))

    # TODO: expand to test for all possible RemoteItemTypes
    @pytest.mark.parametrize("kind,collection_getter", [
        (RemoteItemType.PLAYLIST, partial(Responses.playlist, tracks=True)),
        (RemoteItemType.ALBUM, partial(Responses.album, extend=True, artists=True, tracks=True)),
        # (RemoteItemType.AUDIOBOOK, partial()),
        # (RemoteItemType.SHOW, partial()),
    ])
    def test_get_collections_on_many_strings_multi(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            collection_getter: Callable[[], dict[str, Any]],
            requests_mock: Mocker
    ):
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        items_key = api.collection_item_map[kind].name.casefold() + "s"

        collections_initial = [collection_getter() for _ in range(randrange(5, 10))]
        collection_map = {str(collection["id"]): collection for collection in collections_initial}
        collections_test = random_id_types(id_list=collection_map, api=api, kind=kind)

        for id_, collection in collection_map.items():
            total = collection[api.collection_item_map[kind].name.casefold() + "s"]["total"]
            response_getter = partial(self.get_items_block_json_response, kind=kind, total=total)

            requests_mock.get(url=f"{url}/{id_}", json=collection)
            requests_mock.get(url=re.compile(rf"{url}/{id_}\?"), json=response_getter)

        results = api.get_collections(values=collections_test, kind=kind)
        id_requests = [str(req).split("?")[0].split("/")[-1] for req in requests_mock.request_history]

        assert len(results) == len(collections_initial)
        for result in results:
            collection = collection_map[result["id"]]
            limit = collection[items_key]["limit"]
            total = collection[items_key]["total"]

            assert len(result[items_key]["items"]) == total
            assert id_requests.count(result["id"]) == (total // limit) + 1
            self.assert_results_enriched(results=results, kind=kind)

    def test_get_collections_updates_input_single(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.ALBUM
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        items_key = api.collection_item_map[kind].name.casefold() + "s"
        extended_keys = {"artists", "copyrights", "external_ids", "genres", "label", "popularity"}

        collection_initial = Responses.album(extend=True, artists=True, tracks=True, track_count=randrange(10, 30))
        collection_test = {k: v for k, v in collection_initial.items() if k not in extended_keys}
        total = collection_initial[items_key]["total"]

        assert len(collection_initial[items_key]["items"]) != total
        assert collection_test != collection_initial

        response_getter = partial(self.get_items_block_json_response, kind=kind, total=total)
        requests_mock.get(url=f"{url}/{collection_initial["id"]}", json=collection_initial)
        requests_mock.get(url=re.compile(rf"{url}/{collection_initial["id"]}\?"), json=response_getter)

        results = api.get_collections(values=collection_test, kind=kind)

        assert len(results) == 1
        assert len(results[0][items_key]["items"]) == total
        assert len(collection_test[items_key]["items"]) == total
        assert results[0] == collection_test

    def test_get_collections_updates_input_many(self, api: SpotifyAPI, requests_mock: Mocker):
        kind = RemoteItemType.ALBUM
        url = f"{api.api_url_base}/{kind.name.casefold()}s"
        items_key = api.collection_item_map[kind].name.casefold() + "s"
        extended_keys = {"artists", "copyrights", "external_ids", "genres", "label", "popularity"}

        collections_initial = [Responses.album(extend=True, artists=True, tracks=True, track_count=randrange(10, 30))
                               for _ in range(randrange(2, 5))]
        collection_map = {str(collection["id"]): collection for collection in collections_initial}
        collections_test = {id_: {k: v for k, v in item.items() if k not in extended_keys}
                            for id_, item in collection_map.items()}

        for id_, collection in collection_map.items():
            total = collection[api.collection_item_map[kind].name.casefold() + "s"]["total"]
            response_getter = partial(self.get_items_block_json_response, kind=kind, total=total)

            requests_mock.get(url=f"{url}/{id_}", json=collection)
            requests_mock.get(url=re.compile(rf"{url}/{id_}\?"), json=response_getter)

        results = api.get_collections(values=list(collections_test.values()), kind=kind)

        assert len(results) == len(collections_initial)
        for result in results:
            collection_expected = collection_map[result["id"]]
            collection_test = collections_test[result["id"]]
            total = collection_expected[items_key]["total"]

            assert len(result[items_key]["items"]) == total
            assert len(collection_test[items_key]["items"]) == total
            assert result == collection_test
