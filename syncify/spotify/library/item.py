from abc import ABCMeta
from datetime import datetime
from typing import Any, List, MutableMapping, Optional, Union, Self

from syncify.abstract import Item, Tags
from syncify.spotify.api.utilities import APIMethodInputType
from syncify.spotify import ItemType, IDType
from syncify.spotify.library.response import SpotifyResponse


class SpotifyItem(Item, SpotifyResponse, metaclass=ABCMeta):
    pass


class SpotifyTrack(SpotifyItem, Tags):
    """
    Extracts key ``track`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response.
    :param date_added: Optionally, add a ``date_added`` attribute to this object that represents
        when this track was added to a parent collection.
    """

    _song_keys = {
        0: 'C',
        1: 'C#/Db',
        2: 'D',
        3: 'D#/Eb',
        4: 'E',
        5: 'F',
        6: 'F#/Gb',
        7: 'G',
        8: 'G#/Ab',
        9: 'A',
        10: 'A#/Bb',
        11: 'B'
    }

    def __init__(self, response: MutableMapping[str, Any], date_added: Optional[Union[str, datetime]] = None):
        SpotifyResponse.__init__(self, response=response)

        album = response.get("album", {})
        artists = response.get("artists", {})
        artist_genres = [genre for artist in artists for genre in artist.get("genres", [])]
        genres = album.get("genres") if album.get("genres") else artist_genres

        self.title = response["name"]
        self.artist = self._list_sep.join(artist["name"] for artist in artists)
        self.album = album.get("name")
        self.album_artist = self._list_sep.join(artist["name"] for artist in album.get("artists", []))
        self.track_number = response["track_number"]
        self.track_total = album.get("total_tracks")
        self.genres = genres if genres else None
        self.year = int(album["release_date"][:4]) if album.get("release_date") else None
        self.bpm = None
        self.key = None
        self.disc_number = response["disc_number"]
        self.disc_total = None
        self.compilation = album.get('album_group', "") == "compilation"
        self.comments = None

        images = {image["height"]: image["url"] for image in album.get("images", [])}
        self.image_links = {"cover_front": url for height, url in images.items() if height == max(images)}
        self.has_image = len(self.image_links) > 0

        self.length: float = response['duration_ms'] / 1000
        self.rating: Optional[int] = response.get('popularity')
        self.date_added: Optional[datetime] = date_added
        if isinstance(date_added, str):
            self.date_added = datetime.strptime(date_added, "%Y-%m-%dT%H:%M:%S%z")

        self.artists = [SpotifyArtist(artist) for artist in response["artists"]]

        if not self.album_artist:
            self.album_artist = None

        if "audio_features" in self.response:
            self.bpm = self.response["audio_features"]["tempo"]

            # correctly formatted song key string
            key: str = self._song_keys[self.response["audio_features"]["key"]]
            is_minor: bool = self.response["audio_features"]['mode'] == 0
            if '/' in key:
                key_sep = key.split('/')
                self.key = f"{key_sep[0]}{'m'*is_minor}/{key_sep[1]}{'m'*is_minor}"
            else:
                self.key = f"{key}{'m'*is_minor}"

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)

        id_ = cls.api.extract_ids(value)[0]
        obj.url = cls.api.convert(id_, kind=ItemType.TRACK, type_in=IDType.ID, type_out=IDType.URL)

        obj.reload(use_cache=use_cache)
        return obj

    def refresh(self, use_cache: bool = True) -> None:
        """Quickly refresh this item, calling the stored ``url`` and extracting metadata from the response"""
        self.__init__(self.api.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad))

    def reload(self, use_cache: bool = True) -> None:
        self._check_for_api()

        response = self.api.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_items(response["album"], kind=ItemType.ALBUM, use_cache=use_cache)
        self.api.get_items(response["artists"], kind=ItemType.ARTIST, use_cache=use_cache)
        self.api.get_tracks_extra(response, features=True, use_cache=use_cache)

        self.__init__(response, date_added=getattr(self, "date_added", None))


class SpotifyArtist(SpotifyItem):
    """
    Extracts key ``artist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response.
    """

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.artist: str = response["name"]
        self.genres: Optional[List[str]] = response.get("genres")

        images = {image["height"]: image["url"] for image in response.get("images", [])}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.rating: Optional[int] = response.get('popularity')

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)

        id_ = cls.api.extract_ids(value)[0]
        obj.url = cls.api.convert(id_, kind=ItemType.ARTIST, type_in=IDType.ID, type_out=IDType.URL)

        obj.reload(use_cache=use_cache)
        return obj

    def reload(self, use_cache: bool = True) -> None:
        self.__init__(self.api.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad))
