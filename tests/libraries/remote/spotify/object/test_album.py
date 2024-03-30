import re
from collections.abc import Iterable
from copy import deepcopy
from datetime import date
from random import randrange
from typing import Any

import pytest

from musify.api.exception import APIError
from musify.libraries.remote.core.enum import RemoteObjectType
from musify.libraries.remote.core.exception import RemoteObjectTypeError, RemoteError
from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.object import SpotifyAlbum, SpotifyTrack
from musify.types import Number
from tests.libraries.remote.spotify.api.mock import SpotifyMock
from tests.libraries.remote.spotify.object.testers import SpotifyCollectionLoaderTester
from tests.libraries.remote.spotify.utils import assert_id_attributes


class TestSpotifyAlbum(SpotifyCollectionLoaderTester):

    @pytest.fixture
    def collection(self, response_random: dict[str, Any], api: SpotifyAPI) -> SpotifyAlbum:
        album = SpotifyAlbum(response=response_random, api=api)
        album._tracks = [item for item in album.items if album.items.count(item) == 1]
        return album

    @pytest.fixture
    def collection_merge_items(self, api_mock: SpotifyMock) -> Iterable[SpotifyTrack]:
        return [SpotifyTrack(api_mock.generate_track()) for _ in range(randrange(5, 10))]

    @pytest.fixture
    def item_kind(self, api: SpotifyAPI) -> RemoteObjectType:
        return api.collection_item_map[RemoteObjectType.ALBUM]

    @pytest.fixture
    def response_random(self, api_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for a track item type"""
        response = api_mock.generate_album(track_count=10, use_stored=False)
        response["total_tracks"] = len(response["tracks"]["items"])
        response["tracks"]["total"] = len(response["tracks"]["items"])
        response["tracks"]["next"] = None
        return response

    @pytest.fixture(scope="class")
    def _response_valid(self, api: SpotifyAPI, api_mock: SpotifyMock) -> dict[str, Any]:
        response = next(
            deepcopy(album) for album in api_mock.albums
            if album["tracks"]["total"] > len(album["tracks"]["items"]) > 5 and album["genres"]
            and album["artists"]
        )
        api.extend_items(response=response, key=RemoteObjectType.TRACK)

        api_mock.reset_mock()  # tests check the number of requests made
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
            SpotifyAlbum(api_mock.generate_playlist(item_count=0))
        with pytest.raises(APIError):
            SpotifyAlbum(response_random).reload()

        response_random["total_tracks"] += 10
        with pytest.raises(RemoteError):
            SpotifyAlbum(response_random, skip_checks=False)
        response_random["total_tracks"] -= 20
        with pytest.raises(RemoteError):
            SpotifyAlbum(response_random, skip_checks=False)

    def test_attributes(self, response_random: dict[str, Any]):
        album = SpotifyAlbum(response_random)
        original_response = deepcopy(response_random)

        assert_id_attributes(item=album, response=original_response)

        assert len(album.tracks) == len(original_response["tracks"]["items"])
        for track in album.response["tracks"]["items"]:
            assert "tracks" not in track["album"]
        for track in album.tracks:
            assert track.disc_total == album.disc_total

        assert album.name == album.album
        assert album.album == original_response["name"]
        new_name = "new name"
        album.response["name"] = new_name
        assert album.album == new_name

        original_artists = [artist["name"] for artist in original_response["artists"]]
        assert album.artist == album.tag_sep.join(original_artists)
        assert album.album_artist == album.artist
        assert len(album.artists) == len(original_artists)
        new_artists = ["artist 1", "artist 2"]
        album.response["artists"] = [{"name": artist} for artist in new_artists]
        assert album.artist == album.tag_sep.join(new_artists)
        assert album.album_artist == album.artist

        assert album.track_total == original_response["total_tracks"]
        new_track_total = album.track_total + 20
        album.response["total_tracks"] = new_track_total
        assert album.track_total == new_track_total

        assert album.genres == [g.title() for g in original_response["genres"]]
        new_genres = ["electronic", "dance"]
        album.response["genres"] = new_genres
        assert album.genres == [g.title() for g in new_genres]

        date_split = [int(v) for v in original_response["release_date"].split("-")]
        assert album.year == date_split[0]
        if original_response["release_date_precision"] in {"month", "day"}:
            assert album.month == date_split[1]
        else:
            assert album.month is None
        if original_response["release_date_precision"] in {"day"}:
            assert album.day == date_split[2]
            assert album.date == date(*date_split)
        else:
            assert album.day is None
            assert album.date is None
        new_year = album.year + 20
        new_month = randrange(1, 12)
        new_day = randrange(1, 28)
        album.response["release_date"] = f"{new_year}-{new_month}-{new_day}"
        album.response["release_date_precision"] = "day"
        assert album.date == date(new_year, new_month, new_day)
        assert album.year == new_year
        assert album.month == new_month
        assert album.day == new_day

        album.response["album_type"] = "compilation"
        assert album.compilation
        album.response["album_type"] = "album"
        assert not album.compilation

        if not album.has_image:
            album.response["images"] = [{"height": 200, "url": "old url"}]
        images = {image["height"]: image["url"] for image in album.response["images"]}
        assert len(album.image_links) == 1
        assert album.image_links["cover_front"] == next(url for height, url in images.items() if height == max(images))
        new_image_link = "new url"
        album.response["images"].append({"height": max(images) * 2, "url": new_image_link})
        assert album.image_links["cover_front"] == new_image_link

        original_duration = int(sum(
            track["duration_ms"]
            if isinstance(track["duration_ms"], Number)
            else track["duration_ms"]["totalMilliseconds"]
            for track in original_response["tracks"]["items"]
        ) / 1000)
        assert int(album.length) == original_duration
        for track in album.tracks:
            if isinstance(track.response["duration_ms"], Number):
                track.response["duration_ms"] += 2000
            else:
                track.response["duration_ms"]["totalMilliseconds"] += 2000
        assert int(album.length) == original_duration + (2 * len(album.tracks))

        assert album.rating == original_response["popularity"]
        new_rating = album.rating + 20
        album.response["popularity"] = new_rating
        assert album.rating == new_rating

    def test_refresh(self, response_valid: dict[str, Any]):
        album = SpotifyAlbum(response_valid)
        original_track_count = len(album.tracks)
        original_disc_total = album.disc_total

        album.response["tracks"]["items"] = album.response["tracks"]["items"][:original_track_count // 2]
        album.response["artists"] = [album.response["artists"][0]]
        for track in album.response["tracks"]["items"]:
            track["album"].pop("genres", None)
            track["disc_number"] = original_disc_total + 5

        album.refresh(skip_checks=True)

        assert len(album.tracks) == original_track_count // 2
        assert len(album.artists) == 1
        for track in album.tracks:
            assert "genres" in track.response["album"]
            assert track.disc_total == original_disc_total + 5

    def test_reload(self, response_valid: dict[str, Any], api: SpotifyAPI):
        response_valid.pop("genres", None)
        response_valid.pop("popularity", None)

        is_compilation = response_valid["album_type"] == "compilation"
        if is_compilation:
            response_valid["album_type"] = "album"
        else:
            response_valid["album_type"] = "compilation"

        album = SpotifyAlbum(response_valid)
        assert not album.genres
        assert album.rating is None
        assert album.compilation != is_compilation

        album.api = api
        album.reload(extend_artists=True, extend_features=False)
        assert album.genres
        assert album.rating is not None
        assert album.compilation == is_compilation

    ###########################################################################
    ## Load method tests
    ###########################################################################
    @staticmethod
    def get_load_without_items(
            loader: SpotifyAlbum,
            response_valid: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        return loader.load(response_valid["href"], api=api, extend_tracks=True)

    @pytest.fixture
    def load_items(
            self, response_valid: dict[str, Any], item_key: str, api: SpotifyAPI, api_mock: SpotifyMock
    ) -> list[SpotifyTrack]:
        """
        Extract some item responses from the given ``response_valid`` and remove them from the response.
        This fixture manipulates the ``response_valid`` by removing these items
        and reformatting the values in the items block to ensure 'extend_items' calls can still be run successfully.

        :return: The extracted response as SpotifyTracks.
        """
        api_mock.reset_mock()  # tests check the number of requests made

        # ensure extension of items can be made by reducing available items
        limit = response_valid[item_key]["limit"]
        response_valid[item_key]["items"] = response_valid[item_key][api.items_key][:limit]
        response_items = response_valid[item_key]["items"]
        assert len(response_items) < response_valid[item_key]["total"]

        # produce a list of items for input and ensure all items have this album assigned
        available_ids = {item["id"] for item in response_items}
        limit = len(available_ids) // 2
        items = []
        response_without_items = {k: v for k, v in response_valid.items() if k != item_key}
        for response in response_items[:limit]:
            response = deepcopy(response)
            response["album"] = response_without_items
            items.append(SpotifyTrack(response))

        # ensure all initially available items are covered by the response items and input items
        assert {item["id"] for item in response_items} | {item.id for item in items} == available_ids

        # fix the items block to ensure extension doesn't over/under extend
        response_valid[item_key] = api_mock.format_items_block(
            url=response_valid[item_key]["href"],
            items=response_valid[item_key][api.items_key],
            limit=len(response_valid[item_key][api.items_key]),
            total=response_valid[item_key]["total"],
        )

        return items

    def test_load_with_all_items(
            self, response_valid: dict[str, Any], item_key: str, api: SpotifyAPI, api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        load_items = [SpotifyTrack(response) for response in response_valid[item_key][api.items_key]]
        SpotifyAlbum.load(
            response_valid, api=api, items=load_items, extend_albums=True, extend_tracks=False, extend_features=False
        )

        assert not api_mock.request_history

    def test_load_with_some_items(
            self,
            response_valid: dict[str, Any],
            item_key: str,
            load_items: list[SpotifyTrack],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        kind = RemoteObjectType.ALBUM

        result: SpotifyAlbum = SpotifyAlbum.load(
            response_valid, api=api, items=load_items, extend_tracks=True, extend_features=True
        )

        self.assert_load_with_items_requests(
            response=response_valid, result=result, items=load_items, key=item_key, api_mock=api_mock
        )
        self.assert_load_with_items_extended(
            response=response_valid, result=result, items=load_items, kind=kind, key=item_key, api_mock=api_mock
        )

        # requests for extension data
        expected = api_mock.calculate_pages_from_response(response_valid)
        # -1 for not calling initial page
        assert len(api_mock.get_requests(re.compile(f"{result.url}/{item_key}"))) == expected - 1
        assert len(api_mock.get_requests(re.compile(f"{api.url}/audio-features"))) == expected
        assert not api_mock.get_requests(re.compile(f"{api.url}/artists"))  # did not extend artists

    def test_load_with_some_items_and_no_extension(
            self,
            response_valid: dict[str, Any],
            item_kind: RemoteObjectType,
            item_key: str,
            load_items: list[SpotifyTrack],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        api.extend_items(response_valid, kind=RemoteObjectType.ALBUM, key=item_kind)
        api_mock.reset_mock()

        assert len(response_valid[item_key][api.items_key]) == response_valid[item_key]["total"]
        assert not api_mock.get_requests(response_valid[item_key]["href"])

        result: SpotifyAlbum = SpotifyAlbum.load(
            response_valid, api=api, items=load_items, extend_artists=True, extend_tracks=True, extend_features=True
        )

        self.assert_load_with_items_requests(
            response=response_valid, result=result, items=load_items, key=item_key, api_mock=api_mock
        )

        # requests for extension data
        expected = api_mock.calculate_pages_from_response(response_valid)
        assert not api_mock.get_requests(re.compile(f"{result.url}/{item_key}"))  # already extended on input
        assert len(api_mock.get_requests(re.compile(f"{api.url}/audio-features"))) == expected
        assert api_mock.get_requests(re.compile(f"{api.url}/artists"))  # called the artists endpoint at least once
