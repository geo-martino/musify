from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from random import randrange
from typing import Any
from urllib.parse import parse_qs

import pytest

from syncify import PROGRAM_NAME
from syncify.api.exception import APIError
from syncify.remote.enums import RemoteObjectType
from syncify.remote.exception import RemoteObjectTypeError, RemoteError
from syncify.spotify import URL_API
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.exception import SpotifyCollectionError
from syncify.spotify.library import SpotifyItem
from syncify.spotify.library.object import SpotifyAlbum, SpotifyPlaylist, SpotifyArtist
from syncify.spotify.library.object import SpotifyTrack, SpotifyCollectionLoader
from tests.remote.library.collection import RemoteCollectionTester, RemotePlaylistTester
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.library.utils import assert_id_attributes
from tests.spotify.utils import random_uri


class SpotifyCollectionLoaderTester(RemoteCollectionTester, metaclass=ABCMeta):

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> Iterable[SpotifyItem]:
        raise NotImplementedError

    @staticmethod
    def test_load_without_items(
            collection: SpotifyCollectionLoader,
            response_valid: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        api_mock.reset_mock()  # test checks the number of requests made

        unit = collection.__class__.__name__.removeprefix("Spotify")
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.casefold() + "s"

        test = collection.__class__.load(response_valid["href"], api=api, extend_tracks=True)

        assert test.name == response_valid["name"]
        assert test.id == response_valid["id"]
        assert test.url == response_valid["href"]

        requests = api_mock.get_requests(test.url)
        requests += api_mock.get_requests(f"{test.url}/{key}")
        requests += api_mock.get_requests(f"{collection.api.api_url_base}/audio-features")

        # 1 call for initial collection + (pages - 1) for tracks + (pages) for audio-features
        assert len(requests) == 2 * api_mock.calculate_pages_from_response(test.response)

        # input items given, but no key to search on still loads
        test = collection.__class__.load(response_valid, api=api, items=response_valid.pop(key), extend_tracks=True)

        assert test.name == response_valid["name"]
        assert test.id == response_valid["id"]
        assert test.url == response_valid["href"]

    @staticmethod
    def assert_load_with_tracks(
            cls: type[SpotifyCollectionLoader],
            items: list[SpotifyTrack],
            response: dict[str, Any],
            api: SpotifyAPI,
            api_mock: SpotifyMock,
    ):
        """Run test with assertions on load method with given ``items``"""
        unit = cls.__name__.removeprefix("Spotify")
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.casefold() + "s"

        test = cls.load(response, api=api, items=items, extend_tracks=True)
        assert len(test.response[key]["items"]) == response[key]["total"]
        assert len(test.items) == response[key]["total"]
        assert not api_mock.get_requests(test.url)  # playlist URL was not called

        # requests to extend album start from page 2 onward
        requests = api_mock.get_requests(test.url)
        requests += api_mock.get_requests(f"{test.url}/{key}")
        requests += api_mock.get_requests(f"{api.api_url_base}/audio-features")

        # 0 calls for initial collection + (extend_pages - 1) for tracks + (extend_pages) for audio-features
        # + (get_pages) for audio-features get on response items not in input items
        if kind == RemoteObjectType.PLAYLIST:
            input_ids = {item["track"]["id"] for item in response["tracks"]["items"]} - {item.id for item in items}
        else:
            input_ids = {item["id"] for item in response["tracks"]["items"]} - {item.id for item in items}
        get_pages = api_mock.calculate_pages(limit=test.response[key]["limit"], total=len(input_ids))
        extend_pages = api_mock.calculate_pages_from_response(test.response)
        assert len(requests) == 2 * extend_pages - 1 + get_pages

        # ensure none of the items ids were requested
        input_ids = {item.id for item in items}
        for request in api_mock.get_requests(f"{test.url}/{key}"):
            params = parse_qs(request.query)
            if "ids" not in params:
                continue

            assert not input_ids.intersection(params["ids"][0].split(","))


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
        response = api_mock.generate_playlist(item_count=100)
        response["tracks"]["total"] = len(response["tracks"]["items"])
        response["tracks"]["next"] = None
        return response

    @pytest.fixture
    def _response_valid(self, api: SpotifyAPI, api_mock: SpotifyMock) -> dict[str, Any]:
        response = deepcopy(next(pl for pl in api_mock.user_playlists if pl["tracks"]["total"] > 50))
        api.extend_items(items_block=response, key="tracks")

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

        SpotifyPlaylist.check_total = True
        response_random["tracks"]["total"] += 10
        with pytest.raises(RemoteError):
            SpotifyPlaylist(response_random)
        response_random["tracks"]["total"] -= 20
        with pytest.raises(RemoteError):
            SpotifyPlaylist(response_random)

        SpotifyPlaylist.check_total = False
        pl = SpotifyPlaylist(response_random)
        assert not pl.writeable  # non-user playlists are never writeable

        # no API set, these will not run
        with pytest.raises(APIError):
            pl.reload()
        with pytest.raises(APIError):
            pl.delete()
        with pytest.raises(RemoteError):
            pl.sync()

        SpotifyPlaylist.check_total = True

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
        key = api.collection_item_map[RemoteObjectType.PLAYLIST].name.casefold() + "s"

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

        url = f"{api.api_url_base}/users/{api_mock.user_id}/playlists"
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
        response = deepcopy(next(pl for pl in api_mock.user_playlists if names.count(pl["name"]) == 1))
        api.extend_items(items_block=response, key="tracks")
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
            params = parse_qs(req.query)
            if "uris" in params:
                uri_add += params["uris"][0].split(",")
            elif req.body:
                uri_clear += [t["uri"] for t in req.json()["tracks"]]

        return uri_add, uri_clear


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
        response = deepcopy(next(
            album for album in api_mock.albums
            if album["tracks"]["total"] > len(album["tracks"]["items"]) > 5
            and album["genres"]
        ))
        api.extend_items(items_block=response, key="tracks")

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

        SpotifyAlbum.check_total = True
        response_random["total_tracks"] += 10
        with pytest.raises(RemoteError):
            SpotifyAlbum(response_random)
        response_random["total_tracks"] -= 20
        with pytest.raises(RemoteError):
            SpotifyAlbum(response_random)

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

        assert album.year == int(original_response["release_date"][:4])
        new_year = album.year + 20
        album.response["release_date"] = f"{new_year}-12-01"
        assert album.year == new_year

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

        original_duration = int(sum(track["duration_ms"] for track in original_response["tracks"]["items"]) / 1000)
        assert int(album.length) == original_duration
        for track in album.tracks:
            track.response["duration_ms"] += 2000
        assert int(album.length) == original_duration + (2 * len(album.tracks))

        assert album.rating == original_response["popularity"]
        new_rating = album.rating + 20
        album.response["popularity"] = new_rating
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

        album.api = api
        album.reload(extend_artists=True, extend_tracks=False)
        assert album.genres
        assert album.rating is not None
        assert album.compilation == is_compilation

    def test_load_with_items(self, response_valid: dict[str, Any], api: SpotifyAPI, api_mock: SpotifyMock):
        api_mock.reset_mock()  # test checks the number of requests made
        key = api.collection_item_map[RemoteObjectType.ALBUM].name.casefold() + "s"

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
                album for album in api_mock.artist_albums if any(art["id"] == artist["id"] for art in album["artists"])
            ]
            for artist in api_mock.artists
        }
        id_, albums = next((id_, albums) for id_, albums in artist_album_map.items() if len(albums) >= 10)
        artist = deepcopy(next(artist for artist in api_mock.artists if artist["id"] == id_))

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

        SpotifyAlbum.check_total = False
        artist.reload(extend_albums=True, extend_tracks=False)
        assert {album.id for album in artist._albums} == album_ids
        assert len(artist.artists) == len(artist_names)
        assert set(artist.artists) == artist_names
        assert not artist.tracks

        SpotifyAlbum.check_total = True
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
