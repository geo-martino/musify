from abc import ABCMeta
from collections.abc import MutableMapping
from typing import Any, Self

from abstract.collection import Artist
from syncify.abstract.item import Item, Track
from syncify.spotify.api import APIMethodInputType
from syncify.spotify.base import SpotifyObject
from syncify.spotify.enums import IDType, ItemType
from syncify.spotify.utils import convert, extract_ids
from syncify.utils import UnitCollection
from syncify.utils.helpers import to_collection


class SpotifyItem(Item, SpotifyObject, metaclass=ABCMeta):
    """Generic class for storing a Spotify item."""

    @property
    def uri(self) -> str:  # TODO: this should be implemented by SpotifyObject but logic is invalid
        return self.response["uri"]

    @property
    def has_uri(self) -> bool:  # TODO: this should be implemented by SpotifyObject but logic is invalid
        return not self.response.get("is_local", False)


class SpotifyTrack(Track, SpotifyItem):
    """
    Extracts key ``track`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response.
    """

    _song_keys = ("C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B")

    @property
    def name(self):
        return self.title

    @property
    def title(self) -> str:
        return self.response["name"]

    @property
    def artist(self):
        artists = self.response.get("artists", {})
        artist = self._tag_sep.join(artist["name"] for artist in artists)
        return artist if artist else None

    @property
    def album(self):
        album = self.response.get("album", {})
        return album.get("name")

    @property
    def album_artist(self):
        album = self.response.get("album", {})
        album_artist = self._tag_sep.join(artist["name"] for artist in album.get("artists", []))
        return album_artist if album_artist else None

    @property
    def track_number(self) -> int:
        return self.response["track_number"]

    @property
    def track_total(self):
        album = self.response.get("album", {})
        return album.get("total_tracks")

    @property
    def genres(self):
        """
        List of genres for the album this track is featured on.
        If not found, genres from the main artist are given.
        """
        album = self.response.get("album", {})
        if album.get("genres"):
            return [g.title() for g in album.get("genres")]

        artists = self.response.get("artists", {})
        if not artists:
            return

        main_artist_genres = artists[0].get("genres", [])
        return [g.title() for g in main_artist_genres] if main_artist_genres else None

    @property
    def year(self):
        album = self.response.get("album", {})
        return int(album["release_date"][:4]) if album.get("release_date") else None

    @property
    def bpm(self):
        if "audio_features" in self.response:
            return self.response["audio_features"]["tempo"]

    @property
    def key(self):
        if "audio_features" in self.response:
            # correctly formatted song key string
            key: str = self._song_keys[self.response["audio_features"]["key"]]
            is_minor: bool = self.response["audio_features"]["mode"] == 0
            if '/' in key:
                key_sep = key.split('/')
                return f"{key_sep[0]}{'m'*is_minor}/{key_sep[1]}{'m'*is_minor}"
            else:
                return f"{key}{'m'*is_minor}"

    @property
    def disc_number(self) -> int:
        return self.response["disc_number"]

    @property
    def disc_total(self):
        return self._disc_total

    @disc_total.setter
    def disc_total(self, value: int | None):
        self._disc_total = value

    @property
    def compilation(self) -> bool:
        album = self.response.get("album", {})
        return album.get("album_group", "") == "compilation"

    @property
    def comments(self):
        return self._comments

    @comments.setter
    def comments(self, value: UnitCollection[str] | None):
        self._comments = [value] if isinstance(value, str) else to_collection(value, list)

    @property
    def image_links(self):
        album = self.response.get("album", {})
        images = {image["height"]: image["url"] for image in album.get("images", [])}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def has_image(self):
        images = self.response.get("album", {}).get("images", [])
        return images is not None and len(images) > 0

    @property
    def length(self):
        return self.response["duration_ms"] / 1000

    @property
    def rating(self):
        return self.response.get("popularity")

    def __init__(self, response: MutableMapping[str, Any]):
        Track.__init__(self)
        SpotifyObject.__init__(self, response=response)

        self._disc_total = None
        self._comments = None

        self.artists = list(map(SpotifyArtist, response.get("artists", {})))

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)

        # set a mock response with URL to load from
        id_ = extract_ids(value)[0]
        obj.response = {"href": convert(id_, kind=ItemType.TRACK, type_in=IDType.ID, type_out=IDType.URL)}
        obj.reload(use_cache=use_cache)
        return obj

    def refresh(self, use_cache: bool = True) -> None:
        """Quickly refresh this item, calling the stored ``url`` and extracting metadata from the response"""
        self.__init__(self.api.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad))

    def reload(self, use_cache: bool = True):
        self._check_for_api()

        # reload with enriched data
        response = self.api.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_items(response["album"], kind=ItemType.ALBUM, use_cache=use_cache)
        self.api.get_items(response["artists"], kind=ItemType.ARTIST, use_cache=use_cache)
        self.api.get_tracks_extra(response, features=True, use_cache=use_cache)

        self.__init__(response)


class SpotifyArtist(SpotifyItem):
    """
    Extracts key ``artist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response.
    """

    @property
    def name(self):
        return self.artist

    @property
    def artist(self) -> str:
        """The artist's name"""
        return self.response["name"]

    @property
    def genres(self) -> list[str] | None:
        """List of genres associated with this artist"""
        return self.response.get("genres")

    @property
    def image_links(self) -> dict[str, str]:
        """The images associated with this artist in the form ``{image name: image link}``"""
        images = {image["height"]: image["url"] for image in self.response.get("images", [])}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def has_image(self) -> bool:
        """Does the album this track is associated with have an image"""
        images = self.response.get("album", {}).get("images", [])
        return images is not None and len(images) > 0

    @property
    def rating(self) -> int | None:
        """The popularity of this artist on Spotify"""
        return self.response.get("popularity")

    def __init__(self, response: MutableMapping[str, Any]):
        Artist.__init__(self)
        SpotifyObject.__init__(self, response=response)

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)

        # set a mock response with URL to load from
        id_ = extract_ids(value)[0]
        obj.response = {"href": convert(id_, kind=ItemType.ARTIST, type_in=IDType.ID, type_out=IDType.URL)}
        obj.reload(use_cache=use_cache)
        return obj

    def reload(self, use_cache: bool = True):
        self.__init__(self.api.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad))
