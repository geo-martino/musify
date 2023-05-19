from abc import ABCMeta, abstractmethod
from copy import copy
from typing import Any, List, MutableMapping, Optional, Self, Mapping

from syncify.abstract.collection import ItemCollection, Album
from syncify.spotify import ItemType, IDType
from syncify.spotify.api import APIMethodInputType
from syncify.spotify.library.response import SpotifyResponse
from syncify.spotify.library.item import SpotifyTrack, SpotifyArtist, SpotifyItem


class SpotifyCollection(ItemCollection, SpotifyResponse, metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True, items: Optional[List[SpotifyItem]] = None) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        The given ``value`` may be:
            * A string representing a URL/URI/ID.
            * A list of strings representing URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection with a valid ID value under an ``id`` key.
            * A list of Spotify API JSON responses for a collection with a valid ID value under an ``id`` key.

        When a list is given, only the first item is processed.

        :param value: The value representing some Spotify artist. See description for allowed value types.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :param items: Optionally, give a list of available items to build a response for this collection.
            In doing so, the method will first try to find the API responses for the items of this collection
            in the given list before calling the API for any items not found there.
            This helps reduce the number of API calls made on initialisation.
        """

    @classmethod
    def _load_response(cls, value: APIMethodInputType, use_cache: bool = True) -> MutableMapping[str, Any]:
        kind = cls.__name__.casefold().replace("spotify", "")
        item_type = ItemType.from_name(kind)
        key = cls.api.collection_types[item_type.name]

        try:
            cls.api.validate_item_type(value, kind=item_type)
            value: MutableMapping[str, Any]
            assert len(value[key][cls.api.items_key]) == value[key]["total"]
            return value
        except (ValueError, AssertionError, TypeError):
            return cls.api.get_collections(value, kind=item_type, use_cache=use_cache)[0]


class SpotifyAlbum(Album, SpotifyCollection):
    """
    Extracts key ``album`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @property
    def name(self) -> str:
        return self.album

    @property
    def items(self) -> List[SpotifyTrack]:
        return self.tracks

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.artist: str = self.list_sep.join(artist["name"] for artist in response["artists"])
        self.album: str = response["name"]
        self.album_artist: str = self.artist
        self.track_total: int = response["total_tracks"]
        self.genres: Optional[List[str]] = response.get("genres")
        self.year: int = int(response["release_date"][:4])
        self.disc_total: int = 0
        self.compilation: bool = response['album_type'] == "compilation"

        images = {image["height"]: image["url"] for image in response["images"]}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.length: float = 0.0
        self.rating: Optional[int] = response.get('popularity')

        album_only = copy(response)
        for track in response["tracks"]["items"]:
            track["album"] = album_only

        self.artists = [SpotifyArtist(artist) for artist in response["artists"]]
        self.tracks = [SpotifyTrack(track) for track in response["tracks"]["items"]]
        self.length = sum(track.length for track in self.tracks)
        self.disc_total = max(track.disc_number for track in self.tracks)

        for track in self.tracks:
            track.disc_total = self.disc_total

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True,
             items: Optional[List[SpotifyTrack]] = None) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        response = cls._load_response(value, use_cache=use_cache)

        if not items:
            id_ = cls.api.extract_ids(value)[0]
            obj.url = cls.api.convert(id_, kind=ItemType.ALBUM, type_in=IDType.ID, type_out=IDType.URL)
            obj.reload(use_cache=use_cache)
        else:
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in items}
            uri_get: List[str] = []

            for i, track_raw in enumerate(response["tracks"]["items"]):
                track: SpotifyTrack = uri_tracks.get(track_raw["track"]["uri"])
                if track:
                    track_raw.clear()
                    track_raw.update(track.response)
                elif not track_raw["is_local"]:
                    uri_get.append(track_raw["uri"])

            if len(uri_get) > 0:
                tracks_new = cls.api.get_items(uri_get, kind=ItemType.TRACK, use_cache=use_cache)
                cls.api.get_tracks_extra(tracks_new, features=True, use_cache=use_cache)
                uri_tracks: Mapping[str, Mapping[str, Any]] = {r["uri"]: r for r in tracks_new}

                for i, track_raw in enumerate(response["tracks"]["items"]):
                    track: Mapping[str, Any] = uri_tracks.get(track_raw["track"]["uri"])
                    if track:
                        track_raw.clear()
                        track_raw.update(track)

            obj.__init__(response)

        return obj

    def reload(self, use_cache: bool = True) -> None:
        self._check_for_api()

        response = self.api.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_items(response["tracks"]["items"], kind=ItemType.TRACK, use_cache=use_cache)
        self.api.get_tracks_extra(response["tracks"]["items"], features=True, use_cache=use_cache)

        self.__init__(response)
