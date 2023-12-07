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

    @classmethod
    def _load_response(cls, value: APIMethodInputType, use_cache: bool = True) -> dict[str, Any]:
        """
        Call the API to get a new response for a given ``value``.
        ``use_cache`` forces request to return a cached result if available.
        """
        kind = cls.__name__.casefold().replace("spotify", "")
        item_type = RemoteItemType.from_name(kind)[0]
        key = cls.api.collection_types[item_type.name]

        try:  # attempt to get response from the given value alone
            cls.validate_item_type(value, kind=item_type)
            value: dict[str, Any]
            assert len(value[key][cls.api.items_key]) == value[key]["total"]
            return value
        except (ValueError, AssertionError, TypeError):  # reload response from the API
            return cls.api.get_collections(value, kind=item_type, use_cache=use_cache)[0]


class SpotifyAlbum(RemoteAlbum[SpotifyTrack], SpotifyCollection):
    """
    Extracts key ``album`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @property
    def name(self):
        return self.response["name"]

    @property
    def tracks(self) -> list[SpotifyTrack]:
        return self._tracks

    @property
    def artists(self) -> list[SpotifyArtist]:
        return self._artists

    @property
    def artist(self):
        return self.tag_sep.join(artist["name"] for artist in self.response["artists"])

    @property
    def album_artist(self):
        return self.artist

    @property
    def track_total(self):
        return self.response["total_tracks"]

    @property
    def genres(self):
        return self.response.get("genres", [])

    @property
    def year(self):
        return int(self.response["release_date"][:4])

    @property
    def compilation(self):
        return self.response["album_type"] == "compilation"

    @property
    def image_links(self):
        images = {image["height"]: image["url"] for image in self.response["images"]}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def has_image(self):
        return len(self.response["images"]) > 0

    @property
    def length(self):
        lengths = {track.length for track in self.tracks}
        return sum(lengths) if lengths else None

    @property
    def rating(self):
        return self.response.get("popularity")

    def __init__(self, response: MutableMapping[str, Any]):
        super().__init__(response=response)

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

    def reload(self, use_cache: bool = True) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_tracks(response["tracks"]["items"], features=True, use_cache=use_cache)

        self.__init__(response)
