import re
from collections.abc import Callable
from copy import deepcopy
from datetime import datetime
from random import choice, randrange, sample, random
from typing import Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote

from pycountry import countries
from requests_mock.mocker import Mocker
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember
from requests_mock.response import _Context as Context

from syncify.abstract.enums import SyncifyEnum
from syncify.remote.enums import RemoteObjectType as ObjectType
from syncify.spotify import URL_API, URL_EXT, SPOTIFY_SOURCE_NAME
from syncify.spotify.api import SpotifyAPI
from tests.spotify.utils import random_id
from tests.utils import random_str, random_date_str, random_dt, random_genres


# noinspection SpellCheckingInspection
def idfn(value: Any) -> str | None:
    """Generate test ID for Spotify API tests"""
    if isinstance(value, SyncifyEnum):
        return value.name
    return value


# noinspection PyTypeChecker,PyUnresolvedReferences
COUNTRY_CODES: list[str] = tuple(country.alpha_2 for country in countries)
IMAGE_SIZES: tuple[int, ...] = tuple([64, 160, 300, 320, 500, 640, 800, 1000])


class SpotifyMock(Mocker):
    """Generates responses and sets up Spotify API requests mock"""

    range_start = 25
    range_stop = 50

    @property
    def item_type_map(self) -> dict[ObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`ObjectType` to the mocked items mapped as {``id``: <item>}"""
        return {
            ObjectType.PLAYLIST: self.playlists,
            ObjectType.ALBUM: self.albums,
            ObjectType.TRACK: self.tracks,
            ObjectType.ARTIST: self.artists,
            ObjectType.USER: self.users,
        }

    @property
    def item_type_map_user(self) -> dict[ObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`ObjectType` to the mocked user items mapped as {``id``: <item>}"""
        return {
            ObjectType.PLAYLIST: self.user_playlists,
            ObjectType.ALBUM: self.user_albums,
            ObjectType.TRACK: self.user_tracks,
            ObjectType.ARTIST: self.user_artists,
        }

    def __init__(self, **kwargs):
        super().__init__(case_sensitive=True, **kwargs)

        self.setup_search_response()

        # generate initial responses for generic item calls
        self.playlists = [self.generate_playlist() for _ in range(randrange(self.range_start, self.range_stop))]
        # ensure at least one playlist has enough items for playlist operations tests
        self.playlists.append(self.generate_playlist(item_count=30))
        self.albums = [self.generate_album() for _ in range(randrange(self.range_start, self.range_stop))]
        self.tracks = [self.generate_track() for _ in range(randrange(self.range_start, self.range_stop))]
        self.artists = [self.generate_artist() for _ in range(randrange(self.range_start, self.range_stop))]
        self.users = [self.generate_user() for _ in range(randrange(self.range_start, self.range_stop))]

        for playlist in self.playlists:  # ensure all assigned playlist owners are in the list of available users
            playlist["owner"] = {k: v for k, v in choice(self.users).items() if k in playlist["owner"]}

        self.audio_features = {
            t["id"]: self.generate_audio_features(track_id=t["id"], duration_ms=t["duration_ms"]) for t in self.tracks
        }
        self.audio_analysis = {t["id"]: {"track": {"duration": t["duration_ms"] / 1000}} for t in self.tracks}

        self.setup_limited_valid_responses()

        # setup responses as needed for each item type
        playlists_map = {item["id"]: item for item in self.playlists}
        self.setup_items_response(kind=ObjectType.PLAYLIST, id_map=playlists_map, batchable=False)
        for id_, item in playlists_map.items():
            self.setup_items_block_response_from_generator(
                kind=ObjectType.PLAYLIST, id_=id_, item=item, generator=self.generate_playlist_tracks
            )

        albums_map = {item["id"]: item for item in self.albums}
        self.setup_items_response(kind=ObjectType.ALBUM, id_map=albums_map)
        for id_, item in albums_map.items():
            self.setup_items_block_response_from_generator(
                kind=ObjectType.ALBUM, id_=id_, item=item, generator=self.generate_album_tracks
            )

        self.setup_items_response(kind=ObjectType.TRACK, id_map={item["id"]: item for item in self.tracks})
        self.setup_items_response(kind="audio-features", id_map=self.audio_features)
        self.setup_items_response(kind="audio-analysis", id_map=self.audio_analysis, batchable=False)

        self.setup_items_response(kind=ObjectType.ARTIST, id_map={item["id"]: item for item in self.artists})
        self.setup_items_response(
            kind=ObjectType.USER, id_map={item["id"]: item for item in self.users}, batchable=False
        )

        # randomly choose currently authenticated user and setup mock
        self.user = choice(self.users)
        self.user_id = self.user["id"]
        self.get(url=f"{URL_API}/me", json=self.user)

        # generate responses for saved user's item calls and id_map for reference by tests
        self.user_playlists = deepcopy(self.playlists)
        self.user_tracks = [self.format_user_item(deepcopy(item), ObjectType.TRACK) for item in self.tracks]
        self.user_albums = [self.format_user_item(deepcopy(item), ObjectType.ALBUM) for item in self.albums]
        self.user_artists = deepcopy(self.artists)

        # assign currently authenticated user info as owner to user playlists and strip items block
        for playlist in self.user_playlists:
            playlist["owner"] = {k: v for k, v in self.user.items() if k in playlist["owner"]}
            playlist["tracks"] = {"href": playlist["tracks"]["href"], "total": playlist["tracks"]["total"]}

        # setup responses as needed for each item type
        self.setup_items_block_response_from_list(url=f"{URL_API}/me/playlists", items=self.user_playlists)
        self.setup_items_block_response_from_list(
            url=f"{URL_API}/users/{self.user_id}/playlists", items=self.user_playlists
        )
        self.setup_items_block_response_from_list(url=f"{URL_API}/me/tracks", items=self.user_tracks)
        self.setup_items_block_response_from_list(url=f"{URL_API}/me/albums", items=self.user_albums)
        self.setup_items_block_response_from_list(url=f"{URL_API}/me/following", items=self.user_artists)

        self.setup_playlist_operations()

    def get_requests(
            self, url: str, params: dict[str, Any] | None = None, response: dict[str, Any] | None = None
    ) -> list[Request]:
        """Get a get request from the history from the given URL and params"""
        requests = []

        for request in self.request_history:
            match_url = url.strip("/").endswith(request.path.strip("/"))

            match_params = params is None
            if not match_params and request.query:
                for k, v in parse_qs(request.query).items():
                    if k in params and str(params[k]) != v[0]:
                        break
                    match_params = True

            match_response = response is None
            if not match_response and request.body:
                for k, v in request.json().items():
                    if k in response and str(response[k]) != str(v):
                        break
                    match_response = True

            if match_url and match_params and match_response:
                requests.append(request)

        return requests

    def setup_limited_valid_responses(self):
        """Sets up limited number of cross-referenced valid responses for RemoteObject tests"""
        self.tracks[0]["artists"] = deepcopy(self.artists[0:2])
        for artist in self.tracks[0]["artists"]:
            for key in {"followers", "genres", "images", "popularity"}:
                artist.pop(key)

        self.tracks[0]["album"] = deepcopy(self.albums[0])
        self.tracks[0]["album"]["artists"] = deepcopy(self.tracks[0]["artists"])
        for key in {"tracks", "copyrights", "external_ids", "genres", "label", "popularity"}:
            self.tracks[0]["album"].pop(key)

    def setup_search_response(self):
        """Setup requests mock for getting responses from the ``/search`` endpoint"""

        def response_getter(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected batched response from a request with an 'ids' param"""
            req_params = parse_qs(req.query)
            limit = int(req_params["limit"][0])
            offset = int(req_params.get("offset", [0])[0])
            kinds = req_params["type"][0].split(",")

            count = 0
            total = 0
            results = {}
            for kind in kinds:
                values = self.item_type_map[ObjectType.from_name(kind)[0]]
                available = len(values)
                results[kind + "s"] = sample(values, k=min(available, limit - count))
                total += available

            return {
                kind: self.format_items_block(url=url, items=items, offset=offset, limit=limit, total=total)
                for kind, items in results.items()
            }

        url = f"{URL_API}/search"
        self.get(url=re.compile(url + r"\?"), json=response_getter)

    def setup_items_response(
            self, kind: ObjectType | str, id_map: dict[str, dict[str, Any]], batchable: bool = True
    ) -> None:
        """
        Setup requests mock for getting responses from the given ``id_map``.
        Sets up mocks for /{``kind``}?... and /{``kind``}/{id} endpoints.
        """
        def response_getter(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected batched response from a request with an 'ids' param"""
            req_params = parse_qs(req.query)
            req_kind = req.path.split("/")[-1].replace("-", "_")

            id_list = req_params["ids"][0].split(",")
            return {req_kind: [deepcopy(id_map[i]) for i in id_list]}

        url = f"{URL_API}/{kind.name.casefold()}s" if isinstance(kind, ObjectType) else f"{URL_API}/{kind}"
        if batchable:
            self.get(url=re.compile(url + r"\?"), json=response_getter)  # item batched calls

        for id_, item in id_map.items():
            self.get(url=f"{url}/{id_}", json=item)  # item multi calls

    def setup_items_block_response_from_generator(
            self,
            kind: ObjectType,
            id_: str,
            item: dict[str, Any],
            generator: Callable[[dict[str, Any], int], list[dict[str, Any]]],
    ) -> None:
        """
        Setup requests mock for getting item block responses for a given ``item``
        using a given ``generator`` which accepts this item as an argument.
        Sets up mocks for /{``kind``}/{id}/{items_key}... endpoints.
        """
        def response_getter(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected response for an items block from the given ``generator``"""
            req_params = parse_qs(req.query)
            limit = int(req_params["limit"][0])
            offset = int(req_params.get("offset", [0])[0])
            total = item[req.path.split("/")[-1]]["total"]

            items = generator(item, min(total - offset, limit))
            return self.format_items_block(url=req.url, items=items, offset=offset, limit=limit, total=total)

        url = f"{URL_API}/{kind.name.casefold()}s"
        items_key = SpotifyAPI.collection_item_map[kind].name.casefold() + "s"
        self.get(url=re.compile(rf"{url}/{id_}/{items_key}"), json=response_getter)

    def setup_items_block_response_from_list(self, url: str, items: list[dict[str, Any]]) -> None:
        """
        Setup requests mock for dynamically generating responses for a user's saved items from the given ``generator``.
        Not providing a ``user_id`` will set up mocks for /me/{``kind``}?... endpoints.
        Providing a ``user_id`` will set up mocks for /users/{``user_id``}/{``kind``}?... endpoints.
        """
        def response_getter(req: Request, _: Context) -> dict[str, Any]:
            """Dynamically generate expected response for an items block from the given ``generator``"""
            req_params = parse_qs(req.query)
            limit = int(req_params["limit"][0])
            offset = int(req_params.get("offset", [0])[0])

            it = deepcopy(items[offset:min(offset + limit, len(items))])
            items_block = self.format_items_block(url=req.url, items=it, offset=offset, limit=limit, total=len(items))

            if url.endswith("me/following"):  # special case for following artists
                items_block["cursors"] = {"after": items_block["next"], "before": items_block["previous"]}
                items_block.pop("next")
                items_block.pop("previous")
                items_block = {"artists": items_block}

            return items_block

        self.get(url=re.compile(url + r"\?"), json=response_getter)

    def setup_playlist_operations(self) -> None:
        """Generate playlist and setup ``requests_mock`` for playlist operations tests"""
        for playlist in self.user_playlists:
            self.post(url=re.compile(rf"{playlist["href"]}/tracks"), json={"snapshot_id": random_str()})
            self.delete(url=re.compile(rf"{playlist["href"]}/tracks"), json={"snapshot_id": random_str()})
            self.delete(url=re.compile(playlist["href"]), json={"snapshot_id": random_str()})

    @staticmethod
    def format_next_url(url: str, offset: int = 0, limit: int = 20) -> str:
        """Format a `next` style URL for looping through API pages"""
        url_parsed = urlparse(url)
        params: dict[str, Any] = parse_qs(url_parsed.query)
        params["offset"] = offset
        params["limit"] = limit

        url_parts = list(url_parsed[:])
        url_parts[4] = urlencode(params, quote_via=quote)
        return str(urlunparse(url_parts))

    @classmethod
    def format_items_block(
            cls, url: str, items: list[dict[str, Any]], offset: int = 0, limit: int = 20, total: int = 50
    ) -> dict[str, Any]:
        """Format an items block response from a list of items and a URL base."""
        href = cls.format_next_url(url=url, offset=offset, limit=limit)
        limit = max(limit, 1)  # limit must be above 1

        prev_offset = offset - limit
        prev_url = cls.format_next_url(url=url, offset=prev_offset, limit=limit) if prev_offset > 0 else None
        next_offset = offset + limit
        next_url = cls.format_next_url(url=url, offset=next_offset, limit=limit) if next_offset < total else None

        return {
            "href": href,
            "limit": limit,
            "next": next_url,
            "offset": offset,
            "previous": prev_url,
            "total": total,
            "items": items
        }

    @staticmethod
    def format_user_item(response: dict[str, Any], kind: ObjectType) -> dict[str, Any]:
        """Format a response to expected response for a 'saved user's...' endpoint type"""
        return {
            "added_at": random_dt(start=datetime(2008, 10, 7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            kind.name.casefold(): response
        }

    @staticmethod
    def generate_external_ids() -> dict[str, Any]:
        """Return a randomly generated set of external IDs."""
        external_ids = {}

        if choice([True, False]):
            registrant = random_str(3, 3)
            year = str(random_dt().year)[:-2]
            designation = str(randrange(int(10e5), int(10e6 - 1)))
            external_ids["isrc"] = f"{choice(COUNTRY_CODES)}{registrant}{year}{designation}".upper()
        if choice([True, False]):
            external_ids["ran"] = str(randrange(int(10e13), int(10e14 - 1)))
        if choice([True, False]):
            external_ids["upc"] = str(randrange(int(10e12), int(10e13 - 1)))
        return external_ids

    @staticmethod
    def generate_images() -> list[dict[str, Any]]:
        """Return a list of randomly generated Spotify API responses for an image."""
        def generate_image(size: int = choice(IMAGE_SIZES)):
            """Return a randomly generated Spotify API response for an image."""
            return {"url": f"https://i.scdn.co/image/{random_str(40, 40)}", "height": size, "width": size}

        images = [generate_image(size) for size in sample(IMAGE_SIZES, k=randrange(0, len(IMAGE_SIZES)))]
        images.sort(key=lambda x: x["height"], reverse=True)
        return images

    @staticmethod
    def generate_owner(user_id: str = random_id(), user_name: str = random_str(5, 30)) -> dict[str, Any]:
        """Return a randomly generated Spotify API response for an owner"""
        kind = ObjectType.USER.name.lower()
        return {
            "display_name": user_name,
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{user_id}"},
            "href": f"{URL_API}/{kind}s/{user_id}",
            "id": user_id,
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{user_id}",
        }

    @classmethod
    def generate_owner_from_api(cls, api: SpotifyAPI | None = None) -> dict[str, Any]:
        """Return an owner block from the properties of the given :py:class:`SpotifyAPI` object"""
        return cls.generate_owner(user_id=api.user_id, user_name=api.user_name)

    @classmethod
    def generate_user(cls) -> dict[str, Any]:
        """Return a randomly generated Spotify API response for a User."""

        user_id = random_id()
        kind = ObjectType.USER.name.lower()

        response = {
            "country": choice(COUNTRY_CODES),
            "display_name": random_str(5, 30),
            "email": random_str(15, 50),
            "explicit_content": {
                "filter_enabled": choice([True, False]),
                "filter_locked": choice([True, False])
            },
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{user_id}"},
            "followers": {"href": None, "total": randrange(0, int(8e10))},
            "href": f"{URL_API}/{kind}s/{user_id}",
            "id": user_id,
            "images": cls.generate_images(),
            "product": choice(["premium", "free", "open"]),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{user_id}"
        }

        return response

    @classmethod
    def generate_artist(cls, properties: bool = True) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Artist.

        :param properties: Add extra randomly generated information to the response as per documentation.
        """
        artist_id = random_id()
        kind = ObjectType.ARTIST.name.lower()

        response = {
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{artist_id}"},
            "href": f"{URL_API}/{kind}s/{artist_id}",
            "id": artist_id,
            "name": random_str(5, 30),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{artist_id}"
        }

        return cls.extend_artist(response=response, properties=properties)

    @classmethod
    def extend_artist(cls, response: dict[str, Any], properties: bool = True) -> dict[str, Any]:
        """
        Extend a given randomly generated Spotify API ``response`` for an Artist.

        :param response: The response to extend.
        :param properties: Add extra randomly generated information to the response as per documentation.
        """
        if properties:
            response |= {
                "followers": {"href": None, "total": randrange(0, int(8e10))},
                "genres": random_genres(),
                "images": cls.generate_images(),
                "popularity": randrange(0, 100)
            }
        return response

    @classmethod
    def generate_track(cls, album: bool = True, artists: bool = True) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for a Track.

        :param album: Add randomly generated album information to the response as per documentation.
        :param artists: Add randomly generated artists information to the response as per documentation.
        """
        track_id = random_id()
        kind = ObjectType.TRACK.name.lower()

        response = {
            "available_markets": sample(COUNTRY_CODES, k=randrange(1, 5)),
            "disc_number": randrange(1, 4),
            "duration_ms": randrange(int(10e4), int(6*10e6)),  # 1 second to 10 minutes range
            "explicit": choice([True, False, None]),
            "external_ids": cls.generate_external_ids(),
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{track_id}"},
            "href": f"{URL_API}/{kind}s/{track_id}",
            "id": track_id,
            "name": random_str(10, 30),
            "popularity": randrange(0, 100),
            "preview_url": None,
            "track_number": randrange(1, 30),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{track_id}",
            "is_local": False
        }

        return cls.extend_track(response=response, album=album, artists=artists)

    @classmethod
    def extend_track(cls, response: dict[str, Any], album: bool = False, artists: bool = False) -> dict[str, Any]:
        """
        Extend a given randomly generated Spotify API ``response`` for a Track.

        :param response: The response to extend.
        :param album: Add randomly generated album information to the response as per documentation.
        :param artists: Add randomly generated artists information to the response as per documentation.
        """
        if artists:
            response["artists"] = [cls.generate_artist(properties=False) for _ in range(randrange(1, 4))]

        if album:
            response["album"] = cls.generate_album(properties=False, artists=not artists)
            if artists:
                response["album"]["artists"] = deepcopy(response["artists"])

        return response

    @staticmethod
    def generate_audio_features(
            track_id: str = random_id(), duration_ms: int = randrange(int(10e4), int(6*10e6)),
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Album's tracks.

        :param track_id: The Track ID to use in the response. Will randomly generate if not given.
        :param duration_ms: The duration of the track in ms to use in the response. Will randomly generate if not given.
        """
        kind = ObjectType.TRACK.name.lower()

        # noinspection SpellCheckingInspection
        return {
            "acousticness": random(),
            "analysis_url": f"{URL_API}/audio-analysis/{track_id}",
            "danceability": random(),
            "duration_ms": duration_ms,
            "energy": random(),
            "id": track_id,
            "instrumentalness": random(),
            "key": randrange(-1, 11),
            "liveness": random(),
            "loudness": -random() * 60,
            "mode": choice([0, 1]),
            "speechiness": random(),
            "tempo": random() * 100 + 50,
            "time_signature": randrange(3, 7),
            "track_href": f"{URL_API}/{kind}s/{track_id}",
            "type": "audio_features",
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{track_id}",
            "valence": random()
        }

    @classmethod
    def generate_album(
            cls, track_count: int = randrange(4, 50),
            tracks: bool = True,
            artists: bool = True,
            properties: bool = True,
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Album.

        :param track_count: The total number of tracks this album should have.
        :param tracks: Add randomly generated tracks information to the response as per documentation.
        :param artists: Add randomly generated artists information to the response as per documentation.
        :param properties: Add extra randomly generated properties information to the response as per documentation.
        """
        album_id = random_id()
        kind = ObjectType.ALBUM.name.lower()

        response = {
            "album_type": choice((kind, "single", "compilation")),
            "total_tracks": track_count,
            "available_markets": sample(COUNTRY_CODES, k=randrange(1, 5)),
            "external_urls": {"spotify": f"{URL_EXT}/{kind}s/{album_id}"},
            "href": f"{URL_API}/{kind}s/{album_id}",
            "id": album_id,
            "images": cls.generate_images(),
            "name": random_str(20, 50),
            "release_date": random_date_str(),
            "release_date_precision": choice(("day", "month", "year")),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{album_id}",
        }

        if tracks:
            tracks = cls.generate_album_tracks(response=response)
            url = response["href"] + "/tracks"
            response["tracks"] = cls.format_items_block(url=url, items=tracks, limit=len(tracks), total=track_count)

        response |= cls.generate_album_extras(artists=artists, properties=properties)
        return response

    @classmethod
    def generate_album_tracks(cls, response: dict[str, Any], count: int = 0) -> list[dict[str, Any]]:
        """
        Randomly generate album tracks for a given randomly generated Spotify API Album ``response``.

        :param response: The Album response.
        :param count: The number of tracks to generate.
            If 0, attempt to get this number from the 'limit' key in the 'tracks' key of the response
            or use the 'total' value.
        :return: A list of the randomly generated tracks.
        """
        total = response["total_tracks"]

        # force pagination testing when range > 1
        if not count:
            limit = response.get("tracks", {}).get("limit", total // randrange(1, 4))
            count = limit if limit < total else total

        if response.get("artists"):
            artists = response["artists"]
        else:
            artists = [cls.generate_artist(properties=False) for _ in range(randrange(1, 4))]

        items = [cls.generate_track(album=False, artists=False) for _ in range(count)]
        [item.pop("popularity") for item in items]
        items = [item | {"artists": artists, "track_number": i} for i, item in enumerate(items, 1)]

        return items

    @classmethod
    def generate_album_extras(cls, artists: bool = False, properties: bool = False) -> dict[str, Any]:
        """
        Randomly generate extra album data for a given randomly generated Spotify API Album ``response``.

        :param artists: Add randomly generated artists information to the response as per documentation.
        :param properties: Add extra randomly generated properties information to the response as per documentation.
        """
        extras = {}
        if artists:
            extras["artists"] = [cls.generate_artist(properties=False) for _ in range(randrange(1, 4))]

        if properties:
            extras |= {
                "copyrights": [
                    {"text": random_str(50, 100), "type": i} for i in ["C", "P"][:randrange(1, 2)]
                ],
                "external_ids": cls.generate_external_ids(),
                "genres": random_genres(),
                "label": random_str(50, 100),
                "popularity": randrange(0, 100)
            }

        return extras

    @classmethod
    def generate_playlist(
            cls,
            item_count: int = randrange(0, 200),
            user_id: str | None = random_str(5, 30),
            api: SpotifyAPI | None = None,
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for a Playlist.

        :param item_count: The total number of items this playlist should have.
        :param user_id: An optional ``user_id`` to use as the owner of the playlist.
        :param api: An optional, authenticated :py:class:`SpotifyAPI` object to extract user information from.
        """
        playlist_id = random_id()
        kind = ObjectType.PLAYLIST.name.lower()
        url = f"{URL_API}/{kind}s/{playlist_id}"

        owner = cls.generate_owner_from_api(api=api) if api else cls.generate_owner(user_id=user_id)
        response = {
            "collaborative": choice([True, False]),
            "description": random_str(20, 100),
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{playlist_id}"},
            "followers": {"href": None, "total": randrange(0, int(8e10))},
            "href": url,
            "id": playlist_id,
            "images": cls.generate_images(),
            "name": random_str(5, 50),
            "owner": owner,
            "primary_color": None,
            "public": choice([True, False]),
            "snapshot_id": random_str(60, 60),
            "tracks": {"href": f"{url}/tracks", "total": item_count},
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{playlist_id}",
        }

        tracks = cls.generate_playlist_tracks(response=response)
        url = response["tracks"]["href"]
        response["tracks"] = cls.format_items_block(url=url, items=tracks, limit=len(tracks), total=item_count)

        return response

    @classmethod
    def generate_playlist_tracks(cls, response: dict[str, Any], count: int = 0) -> list[dict[str, Any]]:
        """
        Randomly generate playlist tracks for a given randomly generated Spotify API Playlist ``response``.

        :param response: The Playlist response.
        :param count: The number of tracks to generate.
            If 0, attempt to get this number from the 'limit' key in the 'tracks' key of the response
            or use the 'total' value.
        :return: A list of the randomly generated tracks.
        """
        total = response["tracks"]["total"]

        if not count:
            # force pagination testing when range > 1
            limit = min(50, response["tracks"].get("limit", total // randrange(1, 4)))
            count = limit if limit < total else total

        owner = deepcopy(response["owner"])
        owner.pop("display_name", None)

        items = []
        for _ in range(count):
            track = cls.generate_track(album=True, artists=True) | {"episode": False, "track": True}
            track = cls.format_user_item(response=track, kind=ObjectType.TRACK)
            track |= {"added_by": choice((owner, cls.generate_owner())), "is_local": track["track"]["is_local"]}
            items.append(track)

        return items
