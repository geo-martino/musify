from collections.abc import MutableMapping
from typing import Any, Self

from syncify.remote.api import APIMethodInputType
from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.remote.library.item import RemoteTrack, RemoteArtist
from syncify.spotify.processors.wrangle import SpotifyObjectWranglerMixin
from syncify.utils import UnitCollection
from syncify.utils.helpers import to_collection


class SpotifyTrack(SpotifyObjectWranglerMixin, RemoteTrack):
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
        artist = self.tag_sep.join(artist["name"] for artist in artists)
        return artist if artist else None

    @property
    def album(self):
        album = self.response.get("album", {})
        return album.get("name")

    @property
    def album_artist(self):
        album = self.response.get("album", {})
        album_artist = self.tag_sep.join(artist["name"] for artist in album.get("artists", []))
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
        if "audio_features" not in self.response:
            return
        return self.response["audio_features"]["tempo"]

    @property
    def key(self):
        if "audio_features" not in self.response:
            return

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
        super().__init__(response=response)

        self._disc_total = None
        self._comments = None

        self.artists = list(map(SpotifyArtist, response.get("artists", {})))

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True, *_, **__) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)

        # set a mock response with URL to load from
        id_ = cls.extract_ids(value)[0]
        obj.response = {
            "href": cls.convert(id_, kind=RemoteItemType.TRACK, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        }
        obj.reload(use_cache=use_cache)
        return obj

    def reload(self, use_cache: bool = True) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_items(response["album"], kind=RemoteItemType.ALBUM, use_cache=use_cache)
        self.api.get_items(response["artists"], kind=RemoteItemType.ARTIST, use_cache=use_cache)
        self.api.get_tracks_extra(response, features=True, use_cache=use_cache)

        self.__init__(response)


class SpotifyArtist(SpotifyObjectWranglerMixin, RemoteArtist):
    """Extracts key ``artist`` data from a Spotify API JSON response."""

    @property
    def name(self):
        return self.artist

    @property
    def artist(self):
        return self.response["name"]

    @property
    def genres(self):
        return self.response.get("genres")

    @property
    def image_links(self):
        images = {image["height"]: image["url"] for image in self.response.get("images", [])}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def has_image(self):
        images = self.response.get("album", {}).get("images", [])
        return images is not None and len(images) > 0

    @property
    def length(self):
        return self.response.get("followers", {}).get("total")

    @property
    def rating(self):
        return self.response.get("popularity")

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True, *_, **__) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)

        # set a mock response with URL to load from
        id_ = cls.extract_ids(value)[0]
        obj.response = {
            "href": cls.convert(id_, kind=RemoteItemType.ARTIST, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        }
        obj.reload(use_cache=use_cache)
        return obj

    def reload(self, use_cache: bool = True) -> None:
        self.__init__(self.api.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad))
