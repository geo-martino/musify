from copy import deepcopy
from random import choice, randrange, sample, random
from typing import Any

from pycountry import countries

from syncify.remote.enums import RemoteItemType
from syncify.spotify import URL_API, URL_EXT, SPOTIFY_SOURCE_NAME
from syncify.spotify.api import SpotifyAPI
from tests.spotify.utils import random_id
from tests.utils import random_str, random_date_str, random_dt, random_genres

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
    def format_items_block(
            url_base: str, items: list[dict[str, Any]], offset: int = 0, limit: int = 20
    ) -> dict[str, Any]:
        """Format an items block response from a list of items and a URL base."""
        prev_offset = offset - limit
        next_offset = offset + limit

        return {
            "href": f"{url_base}?offset={offset}&limit={limit}",
            "limit": limit,
            "next": None if len(items) < next_offset else f"{url_base}?offset={next_offset}&limit={limit}",
            "offset": offset,
            "previous": None if prev_offset <= 0 else f"{url_base}?offset={prev_offset}&limit={limit}",
            "total": len(items),
            "items": items
        }

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
    def album(cls, extend: bool = True, artists: bool = True, tracks: bool = False) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Album.

        :param extend: Add extra randomly generated information to the response as per documentation.
        :param artists: Add randomly generated artists information to the response as per documentation.
        :param tracks: Add randomly generated tracks information to the response as per documentation.
        """
        album_id = random_id()
        kind = RemoteItemType.ALBUM.name.lower()
        url = f"{URL_API}/{kind}s/{album_id}"

        response = {
            "album_type": choice((kind, "single", "compilation")),
            "total_tracks": randrange(1, 50),
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
            tracks = cls.album_tracks(url=url, count=response["total_tracks"], artists=response.get("artists"))
            response["tracks"] = tracks

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
            cls,
            url: str = f"{URL_API}/{RemoteItemType.ALBUM.name.lower()}s/{random_id()}",
            count: int = randrange(1, 50),
            artists: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for an Album's tracks.

        :param url: The URL to use for this Album.
        :param count: The number of tracks to generate.
        :param artists: A list of Artist responses to use. Will randomly generate for each track if not given.
        """
        if artists is None:
            artists = cls.artist(extend=False)
        items = [cls.track(album=False, artists=False) for _ in range(count)]
        [item.pop("popularity") for item in items]
        items = [item | {"artists": artists, "track_number": i} for i, item in enumerate(items, 1)]
        return cls.format_items_block(url_base=url, items=items)

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
    def playlist(cls, api: SpotifyAPI = None, tracks: bool = True) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for a Playlist.

        :param api: An optional, authenticated :py:class:`SpotifyAPI` object to extract user information from.
        :param tracks: Add randomly generated tracks information to the response as per documentation.
        """
        playlist_id = random_id()
        kind = RemoteItemType.PLAYLIST.name.lower()
        url = f"{URL_API}/{kind}s/{playlist_id}"

        user_kind = RemoteItemType.USER.name.lower()
        if api:
            user_id = api.user_id
            user_name = api.user_name
        else:
            user_id = random_id()
            user_name = random_str(5, 30)

        owner = {
            "external_urls": {"spotify": f"{URL_EXT}/{user_kind}/{user_id}"},
            "href": f"{URL_API}/{user_kind}s/{user_id}",
            "id": user_id,
            "type": "user",
            "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{user_kind}:{user_id}",
        }

        response = {
            "collaborative": choice([True, False]),
            "description": random_str(20, 100),
            "external_urls": {"spotify": f"{URL_EXT}/{kind}/{playlist_id}"},
            "followers": {"href": None, "total": randrange(0, int(8e10))},
            "href": url,
            "id": playlist_id,
            "images": cls.images(),
            "name": random_str(5, 50),
            "owner": {"display_name": user_name} | owner,
            "primary_color": None,
            "public": choice([True, False]),
            "snapshot_id": random_str(60, 60),
            "tracks": {"href": f"{url}/tracks", "total": randrange(0, 100)},
            "type": "playlist",
            "uri": "spotify:playlist:3cEYpjA9oz9GiPac4AsH4n"
        }

        if tracks:
            response["tracks"] = cls.playlist_tracks(url=url, count=response["tracks"]["total"], owner=owner)

        return response

    @classmethod
    def playlist_tracks(
            cls,
            url: str = f"{URL_API}/{RemoteItemType.PLAYLIST.name.lower()}s/{random_id()}",
            count: int = randrange(1, 50),
            owner: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Return a randomly generated Spotify API response for a Playlist's tracks.

        :param url: The URL to use for this Playlist.
        :param count: The number of tracks to generate.
        :param owner: Owner data to assign to each track response.
            Will randomly generate one owner for all tracks if not given.
        """
        if owner is None:
            user_id = random_id()
            user_kind = RemoteItemType.USER.name.lower()

            owner = {
                "external_urls": {"spotify": f"{URL_EXT}/{user_kind}/{user_id}"},
                "href": f"{URL_API}/{user_kind}s/{user_id}",
                "id": user_id,
                "type": "user",
                "uri": f"{SPOTIFY_SOURCE_NAME.lower()}:{user_kind}:{user_id}",
            }

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

        return cls.format_items_block(url_base=url, items=tracks)
