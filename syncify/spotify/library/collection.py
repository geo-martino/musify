from abc import ABCMeta
from collections.abc import Iterable, MutableMapping, Mapping
from copy import copy, deepcopy
from typing import Any, Self

from syncify.abstract.collection import ItemCollection
from syncify.remote.enums import RemoteObjectType
from syncify.remote.library.collection import RemoteAlbum
from syncify.spotify.library.base import SpotifyItem, SpotifyObjectWranglerMixin
from syncify.spotify.library.item import SpotifyTrack, SpotifyArtist


class SpotifyCollection[T: SpotifyItem](SpotifyObjectWranglerMixin, ItemCollection, metaclass=ABCMeta):
    """Generic class for storing a collection of Spotify tracks."""

    @staticmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        if isinstance(items, Iterable):
            return all(isinstance(item, SpotifyItem) for item in items)
        return isinstance(items, SpotifyItem)

    @classmethod
    def _load_response(cls, value: str | MutableMapping[str, Any], use_cache: bool = True) -> MutableMapping[str, Any]:
        """
        Calls the API to get a new response for a given ``value`` if string given,
        or validates the ``value`` as the correct :py:class:`RemoteObjectType` for this class and returns it if valid.
        ``use_cache`` forces request to return a cached result from the API if available.
        """
        unit = cls.__name__.casefold().replace("spotify", "")
        kind = RemoteObjectType.from_name(unit)[0]

        if isinstance(value, MutableMapping) and cls.get_item_type(value) == kind:
            return deepcopy(value)
        else:  # reload response from the API
            return cls.api.get_items(value, kind=kind, use_cache=use_cache)[0]


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
        if "genres" in self.response:
            return [g.title() for g in self.response["genres"]]
        main_artist_genres = self.response["artists"][0].get("genres", [])
        return [g.title() for g in main_artist_genres] if main_artist_genres else None

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
        album_only.pop("tracks")
        for track in response["tracks"]["items"]:
            track["album"] = album_only

        self._artists = list(map(SpotifyArtist, response["artists"]))
        self._tracks = list(map(SpotifyTrack, response["tracks"]["items"]))

        for track in self.tracks:
            track.disc_total = self.disc_total

    @classmethod
    def load(
            cls,
            value: str | MutableMapping[str, Any],
            use_cache: bool = True,
            items: Iterable[SpotifyTrack] = (),
            *args,
            **kwargs
    ) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        key = cls.api.collection_item_map[RemoteObjectType.ALBUM].name.casefold() + "s"

        if not items or (isinstance(value, Mapping) and (key not in value or cls.api.items_key not in value[key])):
            # no items given, regenerate API response from the URL
            obj._response = {"href": value}
            obj.reload(*args, **kwargs, use_cache=use_cache)
            return obj

        # get response and extend if needed
        response = cls._load_response(value, use_cache=use_cache)

        # attempt to find items for this album in the given items
        uri_tracks_input: dict[str, SpotifyTrack] = {
            track.uri: track for track in items
            if track.has_uri and track.response.get("album", {}).get("id") == response["id"]
        }
        uri_get: list[str] = []

        for track_response in response[key][cls.api.items_key]:
            # loop through the skeleton response for this album
            # find items that match from the given items
            if track_response["uri"] in uri_tracks_input:
                # replace the skeleton response with the response from the track
                track = uri_tracks_input.pop(track_response["uri"])
                track_response.clear()
                track_response |= track.response
            elif not track_response["is_local"]:  # add to get from API list
                uri_get.append(track_response["uri"])

        if len(uri_get) > 0:  # get remaining items from API
            uri_tracks_get = {r["uri"]: r for r in cls.api.get_tracks(uri_get, features=True, use_cache=use_cache)}

            for track_response in response[key][cls.api.items_key]:
                track_new: dict[str, Any] = uri_tracks_get.pop(track_response["uri"], None)
                if track_new:  # replace the skeleton response with the new response
                    track_response.clear()
                    track_response |= track_new

        if len(response[key][cls.api.items_key]) < response["total_tracks"]:
            response[key][cls.api.items_key].extend([track.response for track in uri_tracks_input.values()])
        response[key][cls.api.items_key].sort(key=lambda x: x["track_number"])

        extend_response = cls.api.extend_items(
            response[key], unit=RemoteObjectType.ALBUM.name.casefold() + "s", key=key, use_cache=use_cache
        )
        cls.api.get_tracks_extra(extend_response, features=True, use_cache=use_cache)

        obj.__init__(response)
        return obj

    def reload(
            self, extend_artists: bool = False, extend_tracks: bool = False, use_cache: bool = True, *_, **__
    ) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.get_items(self.url, kind=RemoteObjectType.ALBUM, use_cache=use_cache)[0]
        if extend_artists:
            self.api.get_items(response["artists"], kind=RemoteObjectType.ARTIST, use_cache=use_cache)
        if extend_tracks:
            tracks = response["tracks"]
            self.api.get_tracks_extra(tracks["items"], limit=tracks["limit"], features=True, use_cache=use_cache)

        self.__init__(response)
