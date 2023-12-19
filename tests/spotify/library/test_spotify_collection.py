from copy import deepcopy
from random import randrange
from typing import Any, Iterable
from urllib.parse import parse_qs

import pytest

from syncify.api.exception import APIError
from syncify.remote.enums import RemoteObjectType
from syncify.remote.exception import RemoteObjectTypeError
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.library.collection import SpotifyAlbum
from syncify.spotify.library.item import SpotifyTrack
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.library.utils import assert_id_attributes, SpotifyCollectionTester


class TestSpotifyAlbum(SpotifyCollectionTester):

    @staticmethod
    @pytest.fixture
    def collection(response_random: dict[str, Any]) -> SpotifyAlbum:
        return SpotifyAlbum(response_random)

    @staticmethod
    @pytest.fixture
    def collection_merge_items(spotify_mock: SpotifyMock) -> Iterable[SpotifyTrack]:
        return [SpotifyTrack(spotify_mock.generate_track()) for _ in range(randrange(5, 10))]

    @pytest.fixture
    def response_random(self, spotify_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for a track item type"""
        return spotify_mock.generate_album(track_count=10)

    @pytest.fixture
    def response_valid(self, spotify_mock: SpotifyMock) -> dict[str, Any]:
        """
        Yield a valid enriched response with extended artists and albums responses
        from the Spotify API for a track item type.
        """
        return deepcopy(next(
            album for album in spotify_mock.albums if album["tracks"]["total"] > len(album["tracks"]["items"]) > 5
        ))

    def test_input_validation(self, spotify_mock: SpotifyMock):
        with pytest.raises(RemoteObjectTypeError):
            SpotifyAlbum(spotify_mock.generate_artist(properties=False))

        url = spotify_mock.artists[0]["href"]
        with pytest.raises(APIError):
            SpotifyAlbum.load(url)

    def test_attributes(self, response_random: dict[str, Any]):
        album = SpotifyAlbum(response_random)
        original_response = deepcopy(response_random)

        assert_id_attributes(item=album, response=original_response)

        assert album.name == album.album
        assert album.album == original_response["name"]
        new_name = "new name"
        album._response["name"] = new_name
        assert album.album == new_name

        assert len(album.tracks) == len(original_response["tracks"]["items"])
        for track in album.response["tracks"]["items"]:
            assert "tracks" not in track["album"]
        for track in album.tracks:
            assert track.disc_total == album.disc_total

        original_artists = [artist["name"] for artist in original_response["artists"]]
        assert album.artist == album.tag_sep.join(original_artists)
        assert album.album_artist == album.artist
        assert len(album.artists) == len(original_artists)
        new_artists = ["artist 1", "artist 2"]
        album._response["artists"] = [{"name": artist} for artist in new_artists]
        assert album.artist == album.tag_sep.join(new_artists)
        assert album.album_artist == album.artist

        assert album.track_total == original_response["total_tracks"]
        new_track_total = album.track_total + 20
        album._response["total_tracks"] = new_track_total
        assert album.track_total == new_track_total

        assert album.genres == [g.title() for g in original_response["genres"]]
        new_genres = ["electronic", "dance"]
        album._response["genres"] = new_genres
        assert album.genres == [g.title() for g in new_genres]

        assert album.year == int(original_response["release_date"][:4])
        new_year = album.year + 20
        album._response["release_date"] = f"{new_year}-12-01"
        assert album.year == new_year

        album._response["album_type"] = "compilation"
        assert album.compilation
        album._response["album_type"] = "album"
        assert not album.compilation

        if not album.has_image:
            album._response["images"] = [{"height": 200, "url": "old url"}]
        images = {image["height"]: image["url"] for image in album.response["images"]}
        assert len(album.image_links) == 1
        assert album.image_links["cover_front"] == next(url for height, url in images.items() if height == max(images))
        new_image_link = "new url"
        album._response["images"].append({"height": max(images) * 2, "url": new_image_link})
        assert album.image_links["cover_front"] == new_image_link

        original_duration = int(sum(track["duration_ms"] for track in original_response["tracks"]["items"]) / 1000)
        assert int(album.length) == original_duration
        for track in album.tracks:
            track._response["duration_ms"] += 2000
        assert int(album.length) == original_duration + (2 * len(album.tracks))

        assert album.rating == original_response["popularity"]
        new_rating = album.rating + 20
        album._response["popularity"] = new_rating
        assert album.rating == new_rating

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
        assert not album.rating
        assert album.compilation != is_compilation

        SpotifyAlbum.api = api
        album.reload(extend_artists=True)
        print(album.response.keys())
        assert album.genres
        assert album.rating
        assert album.compilation == is_compilation

    def test_load_without_items(self, response_valid: dict[str, Any], api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made

        SpotifyAlbum.api = api
        album = SpotifyAlbum.load(response_valid["href"], extend_tracks=True)

        assert album.name == response_valid["name"]
        assert album.id == response_valid["id"]
        assert album.url == response_valid["href"]

        key = api.collection_item_map[RemoteObjectType.ALBUM].name.casefold() + "s"
        requests = spotify_mock.get_requests(album.url)
        requests += spotify_mock.get_requests(f"{album.url}/{key}")
        requests += spotify_mock.get_requests(f"{api.api_url_base}/audio-features")

        pages = (album.response[key]["total"] / album.response[key]["limit"])
        # 1 call for album + (pages - 1) for tracks + (pages) for audio-features
        assert len(requests) == 2 * (int(pages) + (pages % 1 > 0))

        # input items given, but no key to search on still loads
        album = SpotifyAlbum.load(response_valid, items=response_valid.pop(key))

        assert album.name == response_valid["name"]
        assert album.id == response_valid["id"]
        assert album.url == response_valid["href"]

    def test_load_with_items(
            self, response_valid: dict[str, Any], api: SpotifyAPI, spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made
        key = api.collection_item_map[RemoteObjectType.ALBUM].name.casefold() + "s"

        # produce a list of items for input and ensure all items have this album assigned
        available_id_list = {item["id"] for item in response_valid[key]["items"]}
        limit = len(available_id_list) // 2
        items = []
        response_without_items = {k: v for k, v in response_valid.items() if k != key}
        for response in response_valid[key]["items"][:limit]:
            response = deepcopy(response)
            response["album"] = response_without_items
            items.append(SpotifyTrack(response))

        # limit the list of items in the response so that some are in the input items list and some are not
        items_ids_limited = [item["id"] for item in items][:len(available_id_list) // 3]
        response_items = [item for item in response_valid[key]["items"] if item["id"] not in items_ids_limited]
        response_valid[key]["items"] = response_items

        # ensure extension will happen and all initially available items are covered by the response and input items
        assert len(response_valid[key]["items"]) < response_valid[key]["total"]
        assert {item["id"] for item in response_valid[key]["items"] + items} == available_id_list

        SpotifyAlbum.api = api
        album = SpotifyAlbum.load(value=response_valid, items=items)
        assert len(album.response[key]["items"]) == response_valid[key]["total"]
        assert len(album.tracks) == response_valid[key]["total"]

        # assert the input response has not been modified
        assert len(response_valid[key]["items"]) == len(response_items)
        assert len(items) == limit

        # album URL was not called
        assert not spotify_mock.get_requests(album.url)

        # requests to extend album start from page 2 onward
        requests = spotify_mock.get_requests(f"{album.url}/{key}")
        pages = (album.response[key]["total"] / album.response[key]["limit"]) - 1
        assert len(requests) == int(pages) + (pages % 1 > 0)

        # ensure none of the items ids were requested
        input_items_ids = {item["id"] for item in items}
        for request in requests:
            params = parse_qs(request.query)
            if "ids" not in params:
                continue

            assert not input_items_ids.intersection(params["ids"][0].split(","))
