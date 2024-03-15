from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from random import randrange
from typing import Any

import pytest

from musify import PROGRAM_NAME
from musify.shared.api.exception import APIError
from musify.shared.remote.enum import RemoteObjectType
from musify.shared.remote.exception import RemoteObjectTypeError, RemoteError
from musify.spotify.api import SpotifyAPI
from musify.spotify.exception import SpotifyCollectionError
from musify.spotify.object import SpotifyPlaylist
from musify.spotify.object import SpotifyTrack
from tests.shared.remote.object import RemotePlaylistTester
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.testers import SpotifyCollectionLoaderTester
from tests.spotify.utils import random_uri, assert_id_attributes


class TestSpotifyPlaylist(SpotifyCollectionLoaderTester, RemotePlaylistTester):

    @pytest.fixture
    def collection_merge_items(self, api_mock: SpotifyMock) -> Iterable[SpotifyTrack]:
        return [SpotifyTrack(api_mock.generate_track()) for _ in range(randrange(5, 10))]

    @pytest.fixture
    def playlist(self, response_valid: dict[str, Any], api: SpotifyAPI) -> SpotifyPlaylist:
        pl = SpotifyPlaylist(response=response_valid, api=api)
        pl._tracks = [item for item in pl.items if pl.items.count(item) == 1]
        return pl

    @pytest.fixture
    def response_random(self, api_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for a track item type"""
        response = api_mock.generate_playlist(item_count=100, use_stored=False)
        response["tracks"]["total"] = len(response["tracks"]["items"])
        response["tracks"]["next"] = None
        return response

    @pytest.fixture
    def _response_valid(self, api: SpotifyAPI, api_mock: SpotifyMock) -> dict[str, Any]:
        response = next(
            deepcopy(pl) for pl in api_mock.user_playlists
            if pl["tracks"]["total"] > 50 and len(pl["tracks"]["items"]) > 10
        )
        api.extend_items(items_block=response, key=RemoteObjectType.TRACK)

        api_mock.reset_mock()
        return response

    @pytest.fixture
    def response_valid(self, _response_valid: dict[str, Any]) -> dict[str, Any]:
        """
        Yield a valid enriched response with extended artists and albums responses
        from the Spotify API for a track item type. Just a deepcopy of _response_valid fixture.
        """
        return deepcopy(_response_valid)

    def test_input_validation(self, response_random: dict[str, Any], api_mock: SpotifyMock):
        with pytest.raises(RemoteObjectTypeError):
            SpotifyPlaylist(api_mock.generate_album(track_count=0))
        with pytest.raises(APIError):
            SpotifyPlaylist(response_random).reload()

        response_random["tracks"]["total"] += 10
        with pytest.raises(RemoteError):
            SpotifyPlaylist(response_random, skip_checks=False)
        response_random["tracks"]["total"] -= 20
        with pytest.raises(RemoteError):
            SpotifyPlaylist(response_random, skip_checks=False)

        pl = SpotifyPlaylist(response_random, skip_checks=True)
        assert not pl.writeable  # non-user playlists are never writeable

        # no API set, these will not run
        with pytest.raises(APIError):
            pl.reload()
        with pytest.raises(APIError):
            pl.delete()
        with pytest.raises(RemoteError):
            pl.sync()

    def test_writeable(self, response_valid: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        pl = SpotifyPlaylist(response_valid)
        assert pl.owner_id == api_mock.user_id  # ensure this is the currently authorised user's playlist
        assert not pl.writeable  # no API set so not writeable

        pl.api = api
        assert pl.writeable  # currently authorised user's playlists are writeable if scope allows it

    def test_attributes(self, response_random: dict[str, Any]):
        pl = SpotifyPlaylist(response_random)
        original_response = deepcopy(response_random)

        assert_id_attributes(item=pl, response=original_response)

        assert len(pl.tracks) == len(pl.response["tracks"]["items"]) == len(pl._tracks)
        assert pl.track_total == pl.response["tracks"]["total"]

        assert pl.name == original_response["name"]
        new_name = "new name"
        pl.name = new_name
        assert pl.response["name"] == new_name

        assert pl.description == original_response["description"]
        new_description = "new description"
        pl.description = new_description
        assert pl.response["description"] == new_description

        assert pl.public is original_response["public"]
        pl.public = not original_response["public"]
        assert pl.response["public"] is not original_response["public"]

        pl.public = False
        pl.collaborative = True
        assert pl.response["collaborative"]
        pl.public = True
        assert not pl.collaborative
        with pytest.raises(SpotifyCollectionError):
            pl.collaborative = True
        pl.public = False
        pl.collaborative = True
        assert pl.collaborative

        assert pl.followers == original_response["followers"]["total"]
        new_followers = pl.followers + 20
        pl.response["followers"]["total"] = new_followers
        assert pl.followers == new_followers

        assert pl.owner_name == original_response["owner"]["display_name"]
        new_owner_name = "new owner name"
        pl.response["owner"]["display_name"] = new_owner_name
        assert pl.owner_name == new_owner_name

        assert pl.owner_id == original_response["owner"]["id"]
        new_owner_id = "new owner id"
        pl.response["owner"]["id"] = new_owner_id
        assert pl.owner_id == new_owner_id

        if not pl.has_image:
            pl.response["images"] = [{"height": 200, "url": "old url"}]
        images = {image["height"]: image["url"] for image in pl.response["images"]}
        assert len(pl.image_links) == 1
        assert pl.image_links["cover_front"] == next(url for height, url in images.items() if height == max(images))
        new_image_link = "new url"
        pl.response["images"].append({"height": max(images) * 2, "url": new_image_link})
        assert pl.image_links["cover_front"] == new_image_link

        original_uris = [track["track"]["uri"] for track in original_response["tracks"]["items"]]
        assert original_uris == pl._get_track_uris_from_api_response()

        assert len(pl.date_added) == len(set(original_uris))
        assert pl.date_created == min(pl.date_added.values())
        assert pl.date_modified == max(pl.date_added.values())
        new_min_dt = datetime.strptime("2000-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        new_max_dt = datetime.now().replace(tzinfo=None).replace(microsecond=0)
        pl.response["tracks"]["items"].extend([
            {"added_at": new_min_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "track": {"uri": random_uri()}},
            {"added_at": new_max_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "track": {"uri": random_uri()}},
        ])
        assert len(pl.date_added) == len(set(original_uris)) + 2
        assert pl.date_created == new_min_dt
        assert pl.date_modified == new_max_dt

    def test_refresh(self, response_valid: dict[str, Any]):
        pl = SpotifyPlaylist(response_valid, skip_checks=True)
        original_track_count = len(pl.tracks)
        pl.response["tracks"]["items"] = pl.response["tracks"]["items"][:original_track_count // 2]

        pl.refresh(skip_checks=True)
        assert len(pl.tracks) == original_track_count // 2

    def test_reload(self, response_valid: dict[str, Any], api: SpotifyAPI):
        response_valid["description"] = None
        response_valid["public"] = not response_valid["public"]
        response_valid["collaborative"] = not response_valid["collaborative"]

        pl = SpotifyPlaylist(response_valid)
        assert pl.description is None
        assert pl.public is response_valid["public"]
        assert pl.collaborative is response_valid["collaborative"]

        pl.api = api
        pl.reload(extend_artists=True)
        assert pl.description
        assert pl.public is not response_valid["public"]
        assert pl.collaborative is not response_valid["collaborative"]

    def test_load_with_items(self, response_valid: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made
        key = api.collection_item_map[RemoteObjectType.PLAYLIST].name.lower() + "s"

        # ensure extension can be made by reducing available items and adding next page URL
        response_valid[key]["items"] = response_valid[key]["items"][:response_valid[key]["limit"]]
        response_valid[key]["next"] = SpotifyAPI.format_next_url(
            url=response_valid[key]["href"], offset=response_valid[key]["limit"], limit=response_valid[key]["limit"]
        )

        # produce a list of items for input and ensure all items have this album assigned
        available_ids = {item["track"]["id"] for item in response_valid[key]["items"]}
        limit = len(available_ids) // 2
        items = [SpotifyTrack(response["track"]) for response in deepcopy(response_valid[key]["items"][:limit])]
        for item in response_valid[key]["items"]:
            item["track"].pop("popularity")

        # ensure extension will happen and all initially available items are covered by the response and input items
        assert len(response_valid[key]["items"]) < response_valid[key]["total"]
        ids = {item["track"]["id"] for item in response_valid[key]["items"]} | {item.id for item in items}
        assert ids == available_ids

        self.assert_load_with_tracks(
            cls=SpotifyPlaylist, items=items, response=response_valid, api=api, api_mock=api_mock
        )

    def test_create_playlist(self, api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        name = "new playlist"
        pl = SpotifyPlaylist.create(api=api, name="new playlist", public=False, collaborative=True)

        url = f"{api.url}/users/{api_mock.user_id}/playlists"
        body = api_mock.get_requests(url=url, response={"name": name})[0].json()

        assert body["name"] == name
        assert PROGRAM_NAME in body["description"]
        assert not body["public"]
        assert body["collaborative"]

        assert pl.name == name
        assert PROGRAM_NAME in pl.description
        assert not pl.public
        assert pl.collaborative

    def test_delete_playlist(self, response_valid: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made

        names = [pl["name"] for pl in api_mock.user_playlists]
        response = next(deepcopy(pl) for pl in api_mock.user_playlists if names.count(pl["name"]) == 1)
        api.extend_items(items_block=response, key=RemoteObjectType.TRACK)
        pl = SpotifyPlaylist(response=response, api=api)
        url = pl.url

        pl.delete()
        assert api_mock.get_requests(url=url + "/followers")
        assert not pl.response

    ###########################################################################
    ## Sync tests set up
    ###########################################################################

    @pytest.fixture
    def sync_playlist(self, response_valid: dict[str, Any], api: SpotifyAPI) -> SpotifyPlaylist:
        return SpotifyPlaylist(response=response_valid, api=api)

    @staticmethod
    @pytest.fixture
    def sync_items(
            response_valid: dict[str, Any], response_random: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock,
    ) -> list[SpotifyTrack]:
        api.load_user_data()
        api_mock.reset_mock()  # all sync tests check the number of requests made

        uri_valid = [track["track"]["uri"] for track in response_valid["tracks"]["items"]]
        return [
            SpotifyTrack(track["track"]) for track in response_random["tracks"]["items"]
            if track["track"]["uri"] not in uri_valid
        ]

    @staticmethod
    def get_sync_uris(url: str, api_mock: SpotifyMock) -> tuple[list[str], list[str]]:
        requests = api_mock.get_requests(url=f"{url}/tracks")

        uri_add = []
        uri_clear = []
        for req in requests:
            if not req.body:
                continue

            body = req.json()
            if "uris" in body:
                uri_add += body["uris"]
            elif req.body:
                uri_clear += [t["uri"] for t in body["tracks"]]

        return uri_add, uri_clear
