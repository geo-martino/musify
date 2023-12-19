from abc import ABCMeta, abstractmethod
from copy import deepcopy
from datetime import datetime
from random import randrange
from typing import Any, Iterable
from urllib.parse import parse_qs

import pytest

from syncify import PROGRAM_NAME
from syncify.api.exception import APIError
from syncify.remote.enums import RemoteObjectType
from syncify.remote.exception import RemoteObjectTypeError
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.exception import SpotifyCollectionError
from syncify.spotify.library.collection import SpotifyAlbum, SpotifyPlaylist, SpotifyCollectionLoader
from syncify.spotify.library.item import SpotifyItem
from syncify.spotify.library.item import SpotifyTrack
from tests.remote.library.test_remote_collection import RemoteCollectionTester
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.library.utils import assert_id_attributes
from tests.spotify.utils import random_uri


class SpotifyCollectionLoaderTester(RemoteCollectionTester, metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def collection_merge_items(*args, **kwargs) -> Iterable[SpotifyItem]:
        raise NotImplementedError

    @staticmethod
    def test_load_without_items(
            collection: SpotifyCollectionLoader,
            response_valid: dict[str, Any],
            api: SpotifyAPI,
            spotify_mock: SpotifyMock
    ):
        spotify_mock.reset_mock()  # test checks the number of requests made

        unit = collection.__class__.__name__.casefold().replace("spotify", "")
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.casefold() + "s"

        collection.__class__.api = api
        test = collection.__class__.load(response_valid["href"], extend_tracks=True)

        assert test.name == response_valid["name"]
        assert test.id == response_valid["id"]
        assert test.url == response_valid["href"]

        requests = spotify_mock.get_requests(test.url)
        requests += spotify_mock.get_requests(f"{test.url}/{key}")
        requests += spotify_mock.get_requests(f"{api.api_url_base}/audio-features")

        # 1 call for initial collection + (extend_pages - 1) for tracks + (extend_pages) for audio-features
        extend_pages = (test.response[key]["total"] / test.response[key]["limit"])
        extend_pages = int(extend_pages) + (extend_pages % 1 > 0)  # round up
        assert len(requests) == 2 * extend_pages

        # input items given, but no key to search on still loads
        test = collection.__class__.load(response_valid, items=response_valid.pop(key), extend_tracks=True)

        assert test.name == response_valid["name"]
        assert test.id == response_valid["id"]
        assert test.url == response_valid["href"]

    @staticmethod
    def assert_load_with_tracks(
            cls: type[SpotifyCollectionLoader],
            items: list[SpotifyTrack],
            response: dict[str, Any],
            api: SpotifyAPI,
            spotify_mock: SpotifyMock,
    ):
        """Run test with assertions on load method with given ``items``"""
        unit = cls.__name__.casefold().replace("spotify", "")
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.casefold() + "s"

        cls.api = api
        test = cls.load(value=response, items=items, extend_tracks=True)
        assert len(test.response[key]["items"]) == response[key]["total"]
        assert len(test.items) == response[key]["total"]
        assert not spotify_mock.get_requests(test.url)  # playlist URL was not called

        # requests to extend album start from page 2 onward
        requests = spotify_mock.get_requests(test.url)
        requests += spotify_mock.get_requests(f"{test.url}/{key}")
        requests += spotify_mock.get_requests(f"{api.api_url_base}/audio-features")

        # 0 calls for initial collection + (extend_pages - 1) for tracks + (extend_pages) for audio-features
        # + (get_pages) for audio-features get on response items not in input items
        if kind == RemoteObjectType.PLAYLIST:
            input_ids = {item["track"]["id"] for item in response["tracks"]["items"]} - {item.id for item in items}
        else:
            input_ids = {item["id"] for item in response["tracks"]["items"]} - {item.id for item in items}
        get_pages = (len(input_ids) / test.response[key]["limit"])
        get_pages = int(get_pages) + (get_pages % 1 > 0)  # round up
        extend_pages = (test.response[key]["total"] / test.response[key]["limit"])
        extend_pages = (int(extend_pages) + (extend_pages % 1 > 0))  # round up
        assert len(requests) == 2 * extend_pages - 1 + get_pages

        # ensure none of the items ids were requested
        input_ids = {item.id for item in items}
        for request in spotify_mock.get_requests(f"{test.url}/{key}"):
            params = parse_qs(request.query)
            if "ids" not in params:
                continue

            assert not input_ids.intersection(params["ids"][0].split(","))


class TestSpotifyAlbum(SpotifyCollectionLoaderTester):

    @staticmethod
    @pytest.fixture
    def collection(response_random: dict[str, Any]) -> SpotifyAlbum:
        album = SpotifyAlbum(response_random)
        album._tracks = [item for item in album.items if album.items.count(item) == 1]
        return album

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

    def test_input_validation(self, response_random: dict[str, Any], spotify_mock: SpotifyMock):
        with pytest.raises(RemoteObjectTypeError):
            SpotifyAlbum(spotify_mock.generate_playlist(item_count=0))

        url = spotify_mock.playlists[0]["href"]
        SpotifyAlbum.api = None
        with pytest.raises(APIError):
            SpotifyAlbum.load(url)
        with pytest.raises(APIError):
            SpotifyAlbum(response_random).reload()

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
        assert album.rating is None
        assert album.compilation != is_compilation

        SpotifyAlbum.api = api
        album.reload(extend_artists=True)
        assert album.genres
        assert album.rating is not None
        assert album.compilation == is_compilation

    def test_load_with_items(self, response_valid: dict[str, Any], api: SpotifyAPI, spotify_mock: SpotifyMock):
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
        ids = {item["id"] for item in response_valid[key]["items"]} | {item.id for item in items}
        assert ids == available_id_list

        self.assert_load_with_tracks(
            cls=SpotifyAlbum, items=items, response=response_valid, api=api, spotify_mock=spotify_mock
        )


class TestSpotifyPlaylist(SpotifyCollectionLoaderTester):

    @staticmethod
    @pytest.fixture
    def collection(response_random: dict[str, Any]) -> SpotifyPlaylist:
        pl = SpotifyPlaylist(response_random)
        pl._tracks = [item for item in pl.items if pl.items.count(item) == 1]
        return pl

    @staticmethod
    @pytest.fixture
    def collection_merge_items(spotify_mock: SpotifyMock) -> Iterable[SpotifyTrack]:
        return [SpotifyTrack(spotify_mock.generate_track()) for _ in range(randrange(5, 10))]

    @pytest.fixture
    def response_random(self, spotify_mock: SpotifyMock) -> dict[str, Any]:
        """Yield a randomly generated response from the Spotify API for a track item type"""
        return spotify_mock.generate_playlist(item_count=100)

    @pytest.fixture
    def response_valid(self, spotify_mock: SpotifyMock) -> dict[str, Any]:
        """
        Yield a valid enriched response with extended artists and albums responses
        from the Spotify API for a track item type.
        """
        return deepcopy(next(
            pl for pl in spotify_mock.playlists if pl["tracks"]["total"] > len(pl["tracks"]["items"]) > 5
        ))

    def test_input_validation(self, response_random: dict[str, Any], spotify_mock: SpotifyMock):
        with pytest.raises(RemoteObjectTypeError):
            SpotifyPlaylist(spotify_mock.generate_album(track_count=0))

        url = spotify_mock.playlists[0]["href"]
        SpotifyPlaylist.api = None
        with pytest.raises(APIError):
            SpotifyPlaylist.load(url)
        with pytest.raises(APIError):
            SpotifyPlaylist(response_random).reload()

    def test_attributes(self, response_random: dict[str, Any]):
        pl = SpotifyPlaylist(response_random)
        original_response = deepcopy(response_random)

        assert_id_attributes(item=pl, response=original_response)

        assert pl.name == original_response["name"]
        new_name = "new name"
        pl.name = new_name
        assert pl._response["name"] == new_name

        assert pl.description == original_response["description"]
        new_description = "new description"
        pl.description = new_description
        assert pl._response["description"] == new_description

        assert pl.public is original_response["public"]
        pl.public = not original_response["public"]
        assert pl._response["public"] is not original_response["public"]

        pl.public = False
        pl.collaborative = True
        assert pl._response["collaborative"]
        pl.public = True
        assert not pl.collaborative
        with pytest.raises(SpotifyCollectionError):
            pl.collaborative = True
        pl.public = False
        pl.collaborative = True
        assert pl.collaborative

        assert pl.followers == original_response["followers"]["total"]
        new_followers = pl.followers + 20
        pl._response["followers"]["total"] = new_followers
        assert pl.followers == new_followers

        assert pl.owner_name == original_response["owner"]["display_name"]
        new_owner_name = "new owner name"
        pl._response["owner"]["display_name"] = new_owner_name
        assert pl.owner_name == new_owner_name

        assert pl.owner_id == original_response["owner"]["id"]
        new_owner_id = "new owner id"
        pl._response["owner"]["id"] = new_owner_id
        assert pl.owner_id == new_owner_id

        assert len(pl.tracks) == len(pl.response["tracks"]["items"]) == len(pl._tracks)
        assert pl.track_total == pl.response["tracks"]["total"]

        if not pl.has_image:
            pl._response["images"] = [{"height": 200, "url": "old url"}]
        images = {image["height"]: image["url"] for image in pl.response["images"]}
        assert len(pl.image_links) == 1
        assert pl.image_links["cover_front"] == next(url for height, url in images.items() if height == max(images))
        new_image_link = "new url"
        pl._response["images"].append({"height": max(images) * 2, "url": new_image_link})
        assert pl.image_links["cover_front"] == new_image_link

        original_uris = {track["track"]["uri"] for track in original_response["tracks"]["items"]}
        assert original_uris == pl._get_track_uris_from_api_response()

        assert len(pl.date_added) == len(original_uris)
        assert pl.date_created == min(pl.date_added.values())
        assert pl.date_modified == max(pl.date_added.values())
        new_min_dt = datetime.strptime("2000-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        new_max_dt = datetime.now().replace(tzinfo=None).replace(microsecond=0)
        pl._response["tracks"]["items"].extend([
            {"added_at": new_min_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "track": {"uri": random_uri()}},
            {"added_at": new_max_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "track": {"uri": random_uri()}},
        ])
        assert len(pl.date_added) == len(original_uris) + 2
        assert pl.date_created == new_min_dt
        assert pl.date_modified == new_max_dt

    def test_reload(self, response_valid: dict[str, Any], api: SpotifyAPI):
        response_valid["description"] = None
        response_valid["public"] = not response_valid["public"]
        response_valid["collaborative"] = not response_valid["collaborative"]

        pl = SpotifyPlaylist(response_valid)
        assert pl.description is None
        assert pl.public is response_valid["public"]
        assert pl.collaborative is response_valid["collaborative"]

        SpotifyPlaylist.api = api
        pl.reload(extend_artists=True)
        assert pl.description
        assert pl.public is not response_valid["public"]
        assert pl.collaborative is not response_valid["collaborative"]

    def test_load_with_items(self, response_valid: dict[str, Any], api: SpotifyAPI, spotify_mock: SpotifyMock):
        spotify_mock.reset_mock()  # test checks the number of requests made
        key = api.collection_item_map[RemoteObjectType.PLAYLIST].name.casefold() + "s"

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
            cls=SpotifyPlaylist, items=items, response=response_valid, api=api, spotify_mock=spotify_mock
        )

    def test_create_playlist(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        SpotifyPlaylist.api = api

        name = "new playlist"
        pl = SpotifyPlaylist.create("new playlist", public=False, collaborative=True)

        url = f"{api.api_url_base}/users/{spotify_mock.user_id}/playlists"
        body = spotify_mock.get_requests(url=url, response={"name": name})[0].json()

        assert body["name"] == name
        assert PROGRAM_NAME in body["description"]
        assert not body["public"]
        assert body["collaborative"]

        assert pl.name == name
        assert PROGRAM_NAME in pl.description
        assert not pl.public
        assert pl.collaborative

    def test_delete_playlist(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        SpotifyPlaylist.api = api

        names = [playlist["name"] for playlist in spotify_mock.playlists]
        response = deepcopy(next(pl for pl in spotify_mock.playlists if names.count(pl["name"]) == 1))
        pl = SpotifyPlaylist(response)
        url = pl.url

        pl.delete()
        assert spotify_mock.get_requests(url=url + "/followers")
        assert not pl.response

    def test_sync(self):
        pass  # TODO
