from copy import deepcopy
from random import randrange
from typing import Any, Iterable

import pytest

from syncify.spotify.api import SpotifyAPI
from syncify.api.exception import APIError
from syncify.remote.exception import RemoteObjectTypeError
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
    def collection_merge_items() -> Iterable[SpotifyTrack]:
        return [SpotifyTrack(SpotifyMock.generate_track()) for _ in range(randrange(5, 10))]

    @pytest.fixture
    def response_random(self) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for a track item type"""
        return SpotifyMock.generate_album(track_count=10)

    @pytest.fixture
    def response_valid(self, spotify_mock: SpotifyMock) -> dict[str, Any]:
        """
        Yield a valid enriched response with extended artists and albums responses
        from the Spotify API for a track item type.
        """
        return deepcopy(spotify_mock.albums[0])

    def test_input_validation(self, spotify_mock: SpotifyMock):
        with pytest.raises(RemoteObjectTypeError):
            SpotifyAlbum(SpotifyMock.generate_artist(properties=False))

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

        assert album.genres == original_response["genres"]
        new_genres = ["electronic", "dance"]
        album._response["genres"] = new_genres
        assert album.genres == new_genres

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

    def test_load(self, response_valid, api: SpotifyAPI):
        return  # TODO
        SpotifyAlbum.api = api
        album = SpotifyAlbum.load(response_valid["href"])

        assert album.name == response_valid["name"]
        assert album.id == response_valid["id"]
        assert album.url == response_valid["href"]

    def test_reload(self, response_valid, api: SpotifyAPI):
        return  # TODO
        response_valid.pop("genres", None)
        response_valid.pop("popularity", None)

        was_compilation = response_valid["album_type"] == "compilation"
        if was_compilation:
            response_valid["album_type"] = "album"
        else:
            response_valid["album_type"] = "compilation"

        album = SpotifyAlbum(response_valid)
        assert not album.genres
        assert not album.rating
        assert album.compilation != was_compilation

        SpotifyAlbum.api = api
        album.reload()
        assert album.genres
        assert album.rating
        assert album.compilation == was_compilation
