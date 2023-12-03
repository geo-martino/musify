from abc import ABCMeta
from collections.abc import Mapping, Iterable, MutableMapping
from copy import copy
from typing import Any, Self

from syncify.remote.api import APIMethodInputType
from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.remote.library.collection import RemoteAlbum
from syncify.spotify.base import SpotifyObject
from syncify.spotify.library.item import SpotifyTrack, SpotifyArtist
from syncify.spotify.processors.wrangle import SpotifyObjectWranglerMixin


# noinspection PyShadowingNames
class SpotifyCollection[T: SpotifyObject](SpotifyObjectWranglerMixin, metaclass=ABCMeta):
    """Generic class for storing a collection of Spotify tracks."""

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyObjectWranglerMixin.__init__(self, response=response)

    @classmethod
    def _load_response(cls, value: APIMethodInputType, use_cache: bool = True) -> dict[str, Any]:
        """
        Call the API to get a new response for a given ``value``.
        ``use_cache`` forces request to return a cached result if available.
        """
        kind = cls.__name__.casefold().replace("spotify", "")
        item_type = RemoteItemType.from_name(kind)
        key = cls.api.collection_types[item_type.name]

        try:  # attempt to get response from the given value alone
            cls.validate_item_type(value, kind=item_type)
            value: dict[str, Any]
            assert len(value[key][cls.api.items_key]) == value[key]["total"]
            return value
        except (ValueError, AssertionError, TypeError):  # reload response from the API
            return cls.api.get_collections(value, kind=item_type, use_cache=use_cache)[0]


# TODO: cannot view superclasses, something is messed up with the inheritance here
#  also method/properties do not inherit docstrings from parent classes
class SpotifyAlbum(RemoteAlbum[SpotifyTrack], SpotifyCollection):
    """
    Extracts key ``album`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @property
    def name(self) -> str:
        """The album name"""
        return self.response["name"]

    @property
    def tracks(self) -> list[SpotifyTrack]:
        """The tracks in this collection"""
        return self._tracks

    @property
    def artists(self) -> list[SpotifyArtist]:
        """List of artists ordered by frequency of appearance on the tracks on this album"""
        return self._artists

    @property
    def artist(self) -> str:
        """Joined string representation of all artists on this album ordered by frequency of appearance"""
        return self.tag_sep.join(artist["name"] for artist in self.response["artists"])

    @property
    def album_artist(self) -> str:
        """The album artist for this album"""
        return self.artist

    @property
    def track_total(self) -> int:
        """The total number of items in this collection"""
        return self.response["total_tracks"]

    @property
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks on this album"""
        return self.response.get("genres", [])

    @property
    def year(self) -> int:
        """The year this album was released"""
        return int(self.response["release_date"][:4])

    @property
    def compilation(self) -> bool:
        """Is this album a compilation"""
        return self.response["album_type"] == "compilation"

    @property
    def image_links(self) -> dict[str, str]:
        """The images associated with this album in the form ``{image name: image link}``"""
        images = {image["height"]: image["url"] for image in self.response["images"]}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def has_image(self) -> bool:
        """Does this album have an image"""
        return len(self.response["images"]) > 0

    @property
    def length(self) -> int:
        """Total duration of all tracks on this album in seconds"""
        lengths = {track.length for track in self.tracks}
        return sum(lengths) if lengths else None

    @property
    def rating(self) -> float | None:
        """Rating of this album"""
        return self.response.get("popularity")

    def __init__(self, response: MutableMapping[str, Any]):
        RemoteAlbum.__init__(self, response=response)
        SpotifyCollection.__init__(self, response=response)

        album_only = copy(response)
        for track in response["tracks"]["items"]:
            track["album"] = album_only

        self._artists = list(map(SpotifyArtist, response["artists"]))
        self._tracks = list(map(SpotifyTrack, response["tracks"]["items"]))

        for track in self.tracks:
            track.disc_total = self.disc_total

    @classmethod
    def load(
            cls, value: APIMethodInputType, use_cache: bool = True, items: Iterable[SpotifyTrack] = (), *args, **kwargs
    ) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        The given ``value`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a collection with
                a valid ID value under an ``id`` key.

        When a list is given, only the first item is processed.

        :param value: The value representing some remote artist. See description for allowed value types.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :param items: Optionally, give a list of available items to build a response for this collection.
            In doing so, the method will first try to find the API responses for the items of this collection
            in the given list before calling the API for any items not found there.
            This helps reduce the number of API calls made on initialisation.
        """
        cls._check_for_api()
        obj = cls.__new__(cls)
        response = cls._load_response(value, use_cache=use_cache)

        if not items:  # no items given, regenerate API response from the URL
            id_ = cls.extract_ids(value)[0]
            obj.response = {
                "href": cls.convert(id_, kind=RemoteItemType.ALBUM, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
            }
            obj.reload(use_cache=use_cache)
        else:  # attempt to find items for this album in the given items
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in items}
            uri_get: list[str] = []

            for i, track_raw in enumerate(response["tracks"]["items"]):
                # loop through the skeleton response for this album
                # find items that match from the given items
                track: SpotifyTrack = uri_tracks.get(track_raw["track"]["uri"])
                if track:  # replace the skeleton response with the response from the track
                    track_raw.clear()
                    track_raw |= track.response
                elif not track_raw["is_local"]:  # add to get list
                    uri_get.append(track_raw["uri"])

            if len(uri_get) > 0:  # get remaining items
                tracks_new = cls.api.get_tracks(uri_get, features=True, use_cache=use_cache)
                uri_tracks: Mapping[str, Mapping[str, Any]] = {r["uri"]: r for r in tracks_new}

                for i, track_raw in enumerate(response["tracks"]["items"]):
                    track: Mapping[str, Any] = uri_tracks.get(track_raw["track"]["uri"])
                    if track:  # replace the skeleton response with the new response
                        track_raw.clear()
                        track_raw |= track

            obj.__init__(response)

        return obj

    def reload(self, use_cache: bool = True):
        """
        Reload this object from the API, calling all required endpoints
        to get a complete set of data for this item type

        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        self._check_for_api()

        # reload with enriched data
        response = self.api.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_tracks(response["tracks"]["items"], features=True, use_cache=use_cache)

        self.__init__(response)
