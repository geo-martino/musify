from abc import ABCMeta
from collections.abc import Iterable, MutableMapping, Mapping
from copy import copy, deepcopy
from datetime import datetime
from typing import Any, Self

from syncify.remote.enums import RemoteObjectType
from syncify.remote.library.collection import RemoteAlbum, RemotePlaylist, RemoteCollection, RemoteCollectionLoader
from syncify.spotify.exception import SpotifyCollectionError
from syncify.spotify.library.item import SpotifyItem, SpotifyTrack, SpotifyArtist
from syncify.spotify.library.object import SpotifyObject
from syncify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyCollection[T: SpotifyItem](RemoteCollection[T], SpotifyDataWrangler, metaclass=ABCMeta):
    """Generic class for storing a collection of Spotify objects."""


class SpotifyObjectLoaderMixin[T: SpotifyItem](RemoteCollectionLoader[T], SpotifyObject, metaclass=ABCMeta):
    """Mixin for :py:class:`RemoteCollectionLoader` and :py:class:`SpotifyObject`"""
    pass


class SpotifyCollectionLoader[T: SpotifyItem](SpotifyObjectLoaderMixin[T], SpotifyCollection[T], metaclass=ABCMeta):
    """Generic class for storing a collection of Spotify objects that can be loaded from an API response."""

    @classmethod
    def load(
            cls,
            value: str | MutableMapping[str, Any],
            items: Iterable[SpotifyTrack] = (),
            extend_tracks: bool = False,
            use_cache: bool = True,
            *args,
            **kwargs
    ) -> Self:
        cls._check_for_api()
        unit = cls.__name__.casefold().replace("spotify", "")
        kind = RemoteObjectType.from_name(unit)[0]
        key = cls.api.collection_item_map[kind].name.casefold() + "s"

        obj = cls.__new__(cls)

        # no items given, regenerate API response from the URL
        if not items or (isinstance(value, Mapping) and (key not in value or cls.api.items_key not in value[key])):
            if kind == RemoteObjectType.PLAYLIST:
                value = cls.api.get_playlist_url(value)

            obj._response = {"href": value}
            obj.reload(*args, **kwargs, extend_tracks=extend_tracks, use_cache=use_cache)
            return obj

        # get response
        if isinstance(value, MutableMapping) and cls.get_item_type(value) == kind:
            response = deepcopy(value)
        else:  # reload response from the API
            response = cls.api.get_items(value, kind=kind, use_cache=use_cache)[0]

        # attempt to find items for this track collection in the given items
        if kind == RemoteObjectType.ALBUM:
            uri_tracks_input: dict[str, SpotifyTrack] = {
                track.uri: track for track in items if track.response.get("album", {}).get("id") == response["id"]
            }
        else:
            uri_tracks_input: dict[str, SpotifyTrack] = {track.uri: track for track in items}
        uri_get: list[str] = []

        # loop through the skeleton response for this album, find items that match from the given items
        for track_response in response[key][cls.api.items_key]:
            if kind == RemoteObjectType.PLAYLIST:
                track_response = track_response["track"]

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
                if kind == RemoteObjectType.PLAYLIST:
                    track_response = track_response["track"]

                track_new: dict[str, Any] = uri_tracks_get.pop(track_response["uri"], None)
                if track_new:  # replace the skeleton response with the new response
                    track_response.clear()
                    track_response |= track_new

        if kind == RemoteObjectType.ALBUM:
            if len(response[key][cls.api.items_key]) < response["total_tracks"]:
                response[key][cls.api.items_key].extend([track.response for track in uri_tracks_input.values()])
            response[key][cls.api.items_key].sort(key=lambda x: x["track_number"])

        extend_response = cls.api.extend_items(
            response[key], unit=kind.name.casefold() + "s", key=key, use_cache=use_cache
        )
        if extend_tracks:
            if kind == RemoteObjectType.PLAYLIST:
                extend_response = [item["track"] for item in extend_response]
            cls.api.get_tracks_extra(extend_response, limit=response[key]["limit"], features=True, use_cache=use_cache)

        obj.__init__(response)
        return obj


class SpotifyPlaylist(RemotePlaylist[SpotifyTrack], SpotifyCollectionLoader[SpotifyTrack]):
    """
    Extracts key ``playlist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @staticmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        if isinstance(items, Iterable):
            return all(isinstance(item, SpotifyTrack) for item in items)
        return isinstance(items, SpotifyTrack)

    @property
    def name(self):
        return self.response["name"]

    @name.setter
    def name(self, value: str):
        self._response["name"] = value

    @property
    def description(self):
        return self.response["description"]

    @description.setter
    def description(self, value: str | None):
        self._response["description"] = value

    @property
    def public(self):
        """Can other users access this playlist"""
        return self.response["public"]

    @public.setter
    def public(self, value: bool):
        self._response["public"] = value
        if value and self.collaborative:
            self.collaborative = False

    @property
    def collaborative(self):
        """Are other users allowed to modify this playlist"""
        return self.response["collaborative"]

    @collaborative.setter
    def collaborative(self, value: bool):
        if value and self.public:
            raise SpotifyCollectionError("You can only set collaborative to true on non-public playlists.")
        self._response["collaborative"] = value

    @property
    def followers(self):
        return self.response["followers"]["total"]

    @property
    def owner_name(self):
        return self.response["owner"]["display_name"]

    @property
    def owner_id(self):
        return self.response["owner"]["id"]

    @property
    def tracks(self):
        return self._tracks

    @property
    def track_total(self):
        return self.response["tracks"]["total"]

    @property
    def image_links(self):
        images = {image["height"]: image["url"] for image in self.response["images"]}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def has_image(self):
        return len(self.response["images"]) > 0

    @property
    def date_created(self):
        """:py:class:`datetime` object representing when the first track was added to this playlist"""
        return min(self.date_added.values()) if self.date_added else None

    @property
    def date_modified(self):
        """:py:class:`datetime` object representing when a track was most recently added/removed"""
        return max(self.date_added.values()) if self.date_added else None

    @property
    def date_added(self):
        return {
            track["track"]["uri"]: datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%SZ")
            for track in self.response["tracks"]["items"]
        }

    def __init__(self, response: MutableMapping[str, Any]):
        super().__init__(response=response)

        self._tracks = [SpotifyTrack(track["track"]) for track in response["tracks"]["items"]]

    def reload(self, extend_tracks: bool = False, use_cache: bool = True, *_, **__) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.get_items(self.url, kind=RemoteObjectType.PLAYLIST, use_cache=use_cache)[0]
        if extend_tracks:
            tracks = [track["track"] for track in response["tracks"]["items"]]
            self.api.get_tracks_extra(tracks, limit=response["tracks"]["limit"], features=True, use_cache=use_cache)

        self.__init__(response)

    def _get_track_uris_from_api_response(self) -> set[str]:
        return {track["track"]["uri"] for track in self.response["tracks"]["items"]}


class SpotifyAlbum(RemoteAlbum[SpotifyTrack], SpotifyCollectionLoader[SpotifyTrack]):
    """
    Extracts key ``album`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @staticmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        if isinstance(items, Iterable):
            return all(isinstance(item, SpotifyTrack) for item in items)
        return isinstance(items, SpotifyTrack)

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
