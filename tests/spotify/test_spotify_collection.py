from collections.abc import Iterable
from copy import deepcopy
from datetime import date
from random import randrange
from typing import Any

import pytest

from syncify.shared.api.exception import APIError
from syncify.shared.remote.enum import RemoteObjectType
from syncify.shared.remote.exception import RemoteObjectTypeError, RemoteError
from syncify.shared.types import Number
from syncify.spotify import URL_API
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.object import SpotifyAlbum, SpotifyArtist
from syncify.spotify.object import SpotifyTrack
from tests.shared.remote.object import RemoteCollectionTester
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.testers import SpotifyCollectionLoaderTester
from tests.spotify.utils import assert_id_attributes


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
    def response_random(self, api_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for a track item type"""
        response = api_mock.generate_album(track_count=10)
        response["total_tracks"] = len(response["tracks"]["items"])
        response["tracks"]["total"] = len(response["tracks"]["items"])
        response["tracks"]["next"] = None
        return response

    @pytest.fixture(scope="class")
    def _response_valid(self, api: SpotifyAPI, api_mock: SpotifyMock) -> dict[str, Any]:
        response = next(
            deepcopy(album) for album in api_mock.albums
            if album["tracks"]["total"] > len(album["tracks"]["items"]) > 5 and album["genres"]
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
        album.reload(extend_artists=True, extend_tracks=False)
        assert album.genres
        assert album.rating is not None
        assert album.compilation == is_compilation

    def test_load_with_items(self, response_valid: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made
        key = api.collection_item_map[RemoteObjectType.ALBUM].name.lower() + "s"

        # ensure extension can be made by reducing available items and adding next page URL
        response_valid[key]["items"] = response_valid[key]["items"][:response_valid[key]["limit"]]
        response_valid[key]["next"] = SpotifyAPI.format_next_url(
            url=response_valid[key]["href"], offset=response_valid[key]["limit"], limit=response_valid[key]["limit"]
        )

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
        ids = {item["id"] for item in response_valid[key]["items"]} | {item.id for item in items}
        assert ids == available_id_list

        self.assert_load_with_tracks(
            cls=SpotifyAlbum, items=items, response=response_valid, api=api, api_mock=api_mock
        )


class TestSpotifyArtist(RemoteCollectionTester):

    @pytest.fixture
    def collection(self, response_random: dict[str, Any]) -> SpotifyArtist:
        artist = SpotifyArtist(response_random)
        artist._albums = [item for item in artist.items if artist.items.count(item) == 1]
        return artist

    @pytest.fixture
    def collection_merge_items(self, api_mock: SpotifyMock) -> Iterable[SpotifyAlbum]:
        albums = [api_mock.generate_album() for _ in range(randrange(5, 10))]
        for album in albums:
            album["total_tracks"] = len(album["tracks"]["items"])

        return list(map(SpotifyAlbum, albums))

    @pytest.fixture
    def response_random(self, api_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for an artist item type"""
        artist = api_mock.generate_artist()
        albums = [api_mock.generate_album(tracks=False, artists=False) for _ in range(randrange(5, 10))]
        for album in albums:
            album["artists"] = [deepcopy(artist)]
            album["total_tracks"] = 0

        items_block = api_mock.format_items_block(
            url=f"{URL_API}/artists/{artist["id"]}/albums", items=albums, total=len(albums)
        )
        return artist | {"albums": items_block}

    @pytest.fixture
    def response_valid(self, api_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a valid enriched response from the Spotify API for an artist item type."""
        artist_album_map = {
            artist["id"]: [
                deepcopy(album) for album in api_mock.artist_albums
                if any(art["id"] == artist["id"] for art in album["artists"])
            ]
            for artist in api_mock.artists
        }
        id_, albums = next((id_, albums) for id_, albums in artist_album_map.items() if len(albums) >= 10)
        artist = next(deepcopy(artist) for artist in api_mock.artists if artist["id"] == id_)

        for album in albums:
            tracks = [deepcopy(track) for track in api_mock.tracks if track["album"]["id"] == album["id"]]
            [track.pop("popularity", None) for track in tracks]
            tracks = [track | {"track_number": i} for i, track in enumerate(tracks, 1)]

            album["tracks"] = api_mock.format_items_block(url=album["href"], items=tracks, total=len(tracks))

        items_block = api_mock.format_items_block(
            url=f"{URL_API}/artists/{artist["id"]}/albums", items=albums, total=len(albums)
        )
        return artist | {"albums": items_block}

    def test_input_validation(self, response_random: dict[str, Any], api_mock: SpotifyMock):
        with pytest.raises(RemoteObjectTypeError):
            SpotifyArtist(api_mock.generate_track(artists=False, album=False))
        with pytest.raises(APIError):
            SpotifyArtist(response_random).reload()

    def test_attributes(self, response_random: dict[str, Any]):
        artist = SpotifyArtist(response_random)
        original_response = deepcopy(response_random)

        assert_id_attributes(item=artist, response=original_response)
        assert len(artist.albums) == len(original_response["albums"]["items"])
        assert len(artist.artists) == len({art.name for album in artist.albums for art in album.artists})
        assert len(artist.tracks) == artist.track_total == sum(len(album) for album in artist.albums)

        assert artist.name == artist.artist
        assert artist.artist == original_response["name"]
        new_name = "new name"
        artist.response["name"] = new_name
        assert artist.artist == new_name

        assert artist.genres == original_response["genres"]
        new_genres = ["electronic", "dance"]
        artist.response["genres"] = new_genres
        assert artist.genres == new_genres

        if not artist.has_image:
            artist.response["images"] = [{"height": 200, "url": "old url"}]
        images = {image["height"]: image["url"] for image in artist.response["images"]}
        assert len(artist.image_links) == 1
        assert artist.image_links["cover_front"] == next(url for height, url in images.items() if height == max(images))
        new_image_link = "new url"
        artist.response["images"].append({"height": max(images) * 2, "url": new_image_link})
        assert artist.image_links["cover_front"] == new_image_link

        assert artist.rating == original_response["popularity"]
        new_rating = artist.rating + 20
        artist.response["popularity"] = new_rating
        assert artist.rating == new_rating

        assert artist.followers == original_response["followers"]["total"]
        new_followers = artist.followers + 20
        artist.response["followers"]["total"] = new_followers
        assert artist.followers == new_followers

    def test_refresh(self, response_valid: dict[str, Any]):
        artist = SpotifyArtist(response_valid, skip_checks=True)
        original_album_count = len(artist.albums)
        artist.response["albums"]["items"] = artist.response["albums"]["items"][:original_album_count // 2]

        artist.refresh(skip_checks=True)
        assert len(artist.albums) == original_album_count // 2

    def test_reload(self, response_valid: dict[str, Any], api: SpotifyAPI):
        genres = response_valid.pop("genres", None)
        response_valid.pop("popularity", None)
        response_valid.pop("followers", None)

        albums = response_valid.pop("albums")["items"]
        album_ids = {album["id"] for album in albums}
        artist_names = {artist["name"] for album in albums for artist in album["artists"]}

        artist = SpotifyArtist(response_valid)
        assert not artist.genres
        assert artist.rating is None
        assert artist.followers is None
        assert not artist.albums
        assert not artist.artists
        assert not artist.tracks

        artist.api = api
        artist.reload(extend_albums=False, extend_tracks=True)
        if genres:
            assert artist.genres
        assert artist.rating is not None
        assert artist.followers is not None
        assert not artist.albums
        assert not artist.artists
        assert not artist.tracks

        artist.reload(extend_albums=True, extend_tracks=False)
        assert {album.id for album in artist._albums} == album_ids
        assert len(artist.artists) == len(artist_names)
        assert set(artist.artists) == artist_names
        assert not artist.tracks

        artist.reload(extend_albums=True, extend_tracks=True)
        assert artist.tracks

    def test_load(self, response_valid: dict[str, Any], api: SpotifyAPI):
        artist = SpotifyArtist.load(response_valid["href"], api=api)

        assert artist.name == response_valid["name"]
        assert artist.id == response_valid["id"]
        assert artist.url == response_valid["href"]
        assert not artist.albums
        assert not artist.artists
        assert not artist.tracks

        artist = SpotifyArtist.load(response_valid["href"], api=api, extend_albums=True, extend_tracks=True)
        assert artist.albums
        assert artist.artists
        assert artist.tracks
