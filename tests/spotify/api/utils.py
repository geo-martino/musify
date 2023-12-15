from collections.abc import Callable
from copy import deepcopy
from functools import partial
from random import choice, randrange, sample, random
from typing import Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote

from pycountry import countries
from requests_mock.mocker import Mocker

from syncify.abstract.enums import SyncifyEnum
from syncify.remote.enums import RemoteItemType
from syncify.spotify import URL_API, URL_EXT, SPOTIFY_SOURCE_NAME
from syncify.spotify.api import SpotifyAPI
from tests.spotify.utils import random_id
from tests.utils import random_str, random_date_str, random_dt, random_genres


# noinspection SpellCheckingInspection
def idfn(value: Any) -> str | None:
    """Generate test ID for Spotify API tests"""
    if isinstance(value, SyncifyEnum):
        return value.name
    if callable(value):
        return "generator"
    return value


def assert_limit_parameter_valid(
        test_function: Callable,
        requests_mock: Mocker,
        floor: int = 1,
        ceil: int = 50,
        **kwargs
):
    """Test to ensure the limit value was limited to be within acceptable values."""
    # too small
    test_function(limit=floor - 20, **kwargs)
    params = parse_qs(urlparse(requests_mock.last_request.url).query)
    assert "limit" in params
    assert int(params["limit"][0]) == floor

    # too big
    test_function(limit=ceil + 100, **kwargs)
    params = parse_qs(urlparse(requests_mock.last_request.url).query)
    assert "limit" in params
    assert int(params["limit"][0]) == ceil


# noinspection PyTypeChecker,PyUnresolvedReferences
COUNTRY_CODES: list[str] = tuple(country.alpha_2 for country in countries)
IMAGE_SIZES: tuple[int, ...] = tuple([64, 160, 300, 320, 500, 640, 800, 1000])


class SpotifyTestResponses:
    """Methods for generating random response examples from the Spotify API."""

    @staticmethod
    def image(size: int = choice(IMAGE_SIZES)) -> dict[str, Any]:
        """Return a randomly generated Spotify API response for an image."""
        return {"url": f"https://i.scdn.co/image/{random_str(40, 40)}", "height": size, "width": size}

    @classmethod
    def images(cls) -> list[dict[str, Any]]:
        """Return a list of randomly generated Spotify API responses for an image."""
        images = [cls.image(size) for size in sample(IMAGE_SIZES, k=randrange(0, len(IMAGE_SIZES)))]
        images.sort(key=lambda x: x["height"], reverse=True)
        return images

    @staticmethod
    def isrc() -> str:
        """Return a randomly generated ISRC."""
        year = str(random_dt().year)[:-2]
        return f"{choice(COUNTRY_CODES)}{random_str(3, 3)}{year}{randrange(int(10e5), int(10e6 - 1))}".upper()

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
        prev_url = cls.format_next_url(url=url, offset=prev_offset, limit=limit)
        next_offset = offset + limit
        next_url = cls.format_next_url(url=url, offset=next_offset, limit=limit)

        return {
            "href": href,
            "limit": limit,
            "next": None if total < next_offset else next_url,
            "offset": offset,
            "previous": None if prev_offset <= 0 else prev_url,
            "total": total,
            "items": items
        }

    @classmethod
    def generate_items_block(
            cls, generator: Callable[[int], list[dict[str, Any]]], url: str, total: int,
    ) -> dict[str, Any]:
        """Return a formatted items block from the given ``generator``"""
        pages = 3
        limit = total // pages if 0 < total // pages < total else total
        items = generator(limit)
        return cls.format_items_block(url=url, items=items, limit=limit, total=total)

    @staticmethod
    def owner(user_id: str = random_id(), user_name: str = random_str(5, 30)) -> dict[str, Any]:
        """Return a randomly generated Spotify API response for an owner"""
        kind = RemoteItemType.USER.name.lower()
        return {
            "display_name": user_name,
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{user_id}"},
            "href": f"{URL_API}/{kind}s/{user_id}",
            "id": user_id,
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{user_id}",
        }

    @classmethod
    def owner_from_api(cls, api: SpotifyAPI | None = None) -> dict[str, Any]:
        """Return an owner block from the properties of the given :py:class:`SpotifyAPI` object"""
        return cls.owner(user_id=api.user_id, user_name=api.user_name)

    @classmethod
    def user(cls) -> dict[str, Any]:
        """Return a randomly generated Spotify API response for a User."""

        user_id = random_id()
        kind = RemoteItemType.USER.name.lower()

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
            "images": cls.images(),
            "product": choice(["premium", "free", "open"]),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{user_id}"
        }

        return response

    @classmethod
    def artist(cls, extend: bool = True) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Artist.

        :param extend: Add extra randomly generated information to the response as per documentation.
        """
        artist_id = random_id()
        kind = RemoteItemType.ARTIST.name.lower()

        response = {
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{artist_id}"},
            "href": f"{URL_API}/{kind}s/{artist_id}",
            "id": artist_id,
            "name": random_str(5, 30),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{artist_id}"
        }

        if extend:
            response |= {
                "followers": {"href": None, "total": randrange(0, int(8e10))},
                "genres": random_genres(),
                "images": cls.images(),
                "popularity": randrange(0, 100)
            }

        return response

    @classmethod
    def album(
            cls,
            extend: bool = True,
            artists: bool = True,
            tracks: bool = False,
            track_count: int = randrange(1, 50)
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Album.

        :param extend: Add extra randomly generated information to the response as per documentation.
        :param artists: Add randomly generated artists information to the response as per documentation.
        :param tracks: Add randomly generated tracks information to the response as per documentation.
        :param track_count: The total number of tracks this album should have.
        """
        album_id = random_id()
        kind = RemoteItemType.ALBUM.name.lower()
        url = f"{URL_API}/{kind}s/{album_id}"

        response = {
            "album_type": choice((kind, "single", "compilation")),
            "total_tracks": track_count,
            "available_markets": sample(COUNTRY_CODES, k=randrange(1, 5)),
            "external_urls": {"spotify": f"{URL_EXT}/{kind}s/{album_id}"},
            "href": url,
            "id": album_id,
            "images": cls.images(),
            "name": random_str(20, 50),
            "release_date": random_date_str(),
            "release_date_precision": choice(("day", "month", "year")),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{album_id}",
        }

        if artists:
            response["artists"] = [cls.artist(extend=False) for _ in range(randrange(1, 4))]

        if tracks:
            total = response["total_tracks"]
            generator = partial(cls.album_tracks, artists=response.get("artists"))
            response["tracks"] = cls.generate_items_block(generator=generator, total=total, url=url)

        if extend:
            response |= {
                "copyrights": [
                    {"text": random_str(50, 100), "type": i} for i in ["C", "P"][:randrange(1, 2)]
                ],
                "external_ids": {
                    "isrc": cls.isrc(),
                    "ran": str(randrange(int(10e13), int(10e14 - 1))),
                    "upc": str(randrange(int(10e12), int(10e13 - 1)))
                },
                "genres": random_genres(),
                "label": random_str(50, 100),
                "popularity": randrange(0, 100)
            }

        return response

    @classmethod
    def album_tracks(
            cls, count: int = randrange(1, 50), artists: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Return a randomly generated Spotify API response for an Album's tracks.

        :param count: The total number of tracks to generate.
        :param artists: A list of Artist responses to use. Will randomly generate for each track if not given.
        """
        if artists is None:
            artists = cls.artist(extend=False)

        items = [cls.track(album=False, artists=False) for _ in range(count)]
        [item.pop("popularity") for item in items]
        return [item | {"artists": artists, "track_number": i} for i, item in enumerate(items, 1)]

    @classmethod
    def track(cls, album: bool = False, artists: bool = False) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for a Track.

        :param album: Add randomly generated album information to the response as per documentation.
        :param artists: Add randomly generated artists information to the response as per documentation.
        """
        track_id = random_id()
        kind = RemoteItemType.TRACK.name.lower()

        response = {
            "available_markets": sample(COUNTRY_CODES, k=randrange(1, 5)),
            "disc_number": randrange(1, 4),
            "duration_ms": randrange(int(10e4), int(6*10e6)),  # 1 second to 10 minutes range
            "explicit": choice([True, False, None]),
            "external_ids": {
                "isrc": cls.isrc(),
                "ran": str(randrange(int(10e13), int(10e14 - 1))),
                "upc": str(randrange(int(10e12), int(10e13 - 1)))
            },
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{track_id}"},
            "href": f"{URL_API}/{kind}s/{track_id}",
            "id": track_id,
            "name": random_str(10, 30),
            "popularity": randrange(0, 100),
            "preview_url": None,
            "track_number": random_str(1, 30),
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{track_id}",
            "is_local": False
        }

        if artists:
            response["artists"] = [cls.artist(extend=False) for _ in range(randrange(1, 4))]

        if album:
            response["album"] = cls.album(extend=False, artists=not artists, tracks=False)
            if artists:
                response["album"]["artists"] = deepcopy(response["artists"])

        return response

    @staticmethod
    def audio_features(
            track_id: str = random_id(),
            duration_ms: int = randrange(int(10e4), int(6*10e6)),
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Album's tracks.

        :param track_id: The Track ID to use in the response. Will randomly generate if not given.
        :param duration_ms: The duration of the track in ms to use in the response. Will randomly generate if not given.
        """
        kind = RemoteItemType.TRACK.name.lower()

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
    def playlist(
            cls,
            api: SpotifyAPI | None = None,
            user_id: str | None = None,
            tracks: bool = True,
            item_count: int = randrange(0, 100),
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for a Playlist.

        :param api: An optional, authenticated :py:class:`SpotifyAPI` object to extract user information from.
        :param user_id: An optional ``user_id`` to use as the owner of the playlist.
        :param tracks: Add randomly generated tracks information to the response as per documentation.
        :param item_count: The total number of items this playlist should have.
        """
        playlist_id = random_id()
        kind = RemoteItemType.PLAYLIST.name.lower()
        url = f"{URL_API}/{kind}s/{playlist_id}"

        owner = cls.owner_from_api(api=api) if api else cls.owner(user_id=user_id)
        response = {
            "collaborative": choice([True, False]),
            "description": random_str(20, 100),
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{playlist_id}"},
            "followers": {"href": None, "total": randrange(0, int(8e10))},
            "href": url,
            "id": playlist_id,
            "images": cls.images(),
            "name": random_str(5, 50),
            "owner": deepcopy(owner),
            "primary_color": None,
            "public": choice([True, False]),
            "snapshot_id": random_str(60, 60),
            "tracks": {"href": f"{url}/tracks", "total": item_count},
            "type": kind,
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{kind}:{playlist_id}",
        }

        if tracks:
            owner.pop("display_name", None)
            total = response["tracks"]["total"]
            generator = partial(cls.playlist_tracks, owner=owner)
            response["tracks"] = cls.generate_items_block(generator=generator, total=total, url=url)

        return response

    @classmethod
    def playlist_tracks(
            cls, count: int = randrange(1, 50), owner: dict[str, Any] = None,
    ) -> list[dict[str, Any]]:
        """
        Return a randomly generated Spotify API response for a Playlist's tracks.

        :param count: The number of tracks to generate.
        :param owner: Owner data to assign to each track response.
            Will randomly generate one owner for all tracks if not given.
        """
        if owner is None:
            owner = cls.owner()
            owner.pop("display_name", None)

        tracks = []
        for _ in range(count):
            track = cls.track(album=True, artists=True) | {"episode": False, "track": True}
            track = {
                "added_at": random_dt().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "added_by": owner,
                "is_local": track["is_local"],
                "track": track,
            }
            tracks.append(track)

        return tracks
