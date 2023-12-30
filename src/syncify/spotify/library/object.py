from __future__ import annotations

from abc import ABCMeta
from collections.abc import Iterable, MutableMapping, Mapping
from copy import copy, deepcopy
from datetime import datetime
from typing import Any, Self

from syncify.remote.enums import RemoteObjectType, RemoteIDType
from syncify.remote.library.object import RemoteCollection, RemoteCollectionLoader, RemoteTrack
from syncify.remote.library.object import RemotePlaylist, RemoteAlbum, RemoteArtist
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.exception import SpotifyCollectionError
from syncify.spotify.library import SpotifyObject, SpotifyItem
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from syncify.utils import UnitCollection
from syncify.utils.helpers import to_collection


class SpotifyItemWranglerMixin(SpotifyItem, SpotifyDataWrangler, metaclass=ABCMeta):
    pass


class SpotifyTrack(SpotifyItemWranglerMixin, RemoteTrack):
    """
    Extracts key ``track`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response.
    """

    __slots__ = ("_artists", "_disc_total", "_comments")

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
        return artist or None

    @property
    def artists(self) -> list[SpotifyArtist]:
        return self._artists

    @property
    def album(self):
        return self.response.get("album", {}).get("name")

    @property
    def album_artist(self):
        album = self.response.get("album", {})
        album_artist = self.tag_sep.join(artist["name"] for artist in album.get("artists", []))
        return album_artist or None

    @property
    def track_number(self) -> int:
        return self.response["track_number"]

    @property
    def track_total(self):
        return self.response.get("album", {}).get("total_tracks")

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
        key_value: int = self.response["audio_features"]["key"]
        key: str | None = self._song_keys[key_value] if key_value >= 0 else None
        is_minor: bool = self.response["audio_features"]["mode"] == 0

        if not key:
            return None
        elif '/' in key:
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
        return album.get("album_type", "") == "compilation"

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
        if not images:
            return {}
        return {"cover_front": next(url for height, url in images.items() if height == max(images))}

    @property
    def has_image(self):
        return len(self.response.get("album", {}).get("images", [])) > 0

    @property
    def length(self):
        return self.response["duration_ms"] / 1000

    @property
    def rating(self):
        return self.response.get("popularity")

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None):
        super().__init__(response=response, api=api)

        self._disc_total = None
        self._comments = None

        self._artists = list(map(SpotifyArtist, response.get("artists", {})))

    @classmethod
    def load(cls, value: str | dict[str, Any], api: SpotifyAPI, use_cache: bool = True, *_, **__) -> Self:
        obj = cls.__new__(cls)
        obj.api = api

        # set a mock response with URL to load from
        id_ = cls.extract_ids(value)[0]
        obj.response = {
            "href": cls.convert(id_, kind=RemoteObjectType.TRACK, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        }
        obj.reload(use_cache=use_cache)
        return obj

    def reload(self, use_cache: bool = True, *_, **__) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.handler.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.api.get_items(response["album"], kind=RemoteObjectType.ALBUM, extend=False, use_cache=use_cache)
        self.api.get_items(response["artists"], kind=RemoteObjectType.ARTIST, use_cache=use_cache)
        self.api.get_tracks_extra(response, features=True, use_cache=use_cache)

        self.__init__(response=response, api=self.api)


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
            api: SpotifyAPI,
            items: Iterable[SpotifyTrack] = (),
            extend_tracks: bool = False,
            use_cache: bool = True,
            *args,
            **kwargs
    ) -> Self:
        unit = cls.__name__.removeprefix("Spotify").lower()
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.casefold() + "s"

        # no items given, regenerate API response from the URL
        if not items or (isinstance(value, Mapping) and (key not in value or api.items_key not in value[key])):
            if kind == RemoteObjectType.PLAYLIST:
                value = api.get_playlist_url(value)

            obj = cls.__new__(cls)
            obj.api = api
            obj.response = {"href": value}
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
        for track_response in response[key][api.items_key]:
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
            uri_tracks_get = {r["uri"]: r for r in api.get_tracks(uri_get, features=True, use_cache=use_cache)}

            for track_response in response[key][api.items_key]:
                if kind == RemoteObjectType.PLAYLIST:
                    track_response = track_response["track"]

                track_new: dict[str, Any] = uri_tracks_get.pop(track_response["uri"], None)
                if track_new:  # replace the skeleton response with the new response
                    track_response.clear()
                    track_response |= track_new

        if kind == RemoteObjectType.ALBUM:
            if len(response[key][api.items_key]) < response["total_tracks"]:
                response[key][api.items_key].extend([track.response for track in uri_tracks_input.values()])
            response[key][api.items_key].sort(key=lambda x: x["track_number"])

        extend_response = api.extend_items(
            response[key], unit=kind.name.casefold() + "s", key=key, use_cache=use_cache
        )
        if extend_tracks:
            if kind == RemoteObjectType.PLAYLIST:
                extend_response = [item["track"] for item in extend_response]
            api.get_tracks_extra(extend_response, limit=response[key]["limit"], features=True, use_cache=use_cache)

        return cls(response=response, api=api)


class SpotifyPlaylist(RemotePlaylist[SpotifyTrack], SpotifyCollectionLoader[SpotifyTrack]):
    """
    Extracts key ``playlist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    __slots__ = ("_tracks",)

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
        self.response["name"] = value

    @property
    def description(self):
        return self.response["description"]

    @description.setter
    def description(self, value: str | None):
        self.response["description"] = value

    @property
    def public(self):
        """Can other users access this playlist"""
        return self.response["public"]

    @public.setter
    def public(self, value: bool):
        self.response["public"] = value
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
        self.response["collaborative"] = value

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

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None):
        super().__init__(response=response, api=api)
        self._tracks = [SpotifyTrack(track["track"]) for track in response["tracks"]["items"]]
        self._check_total()

    def reload(self, extend_tracks: bool = False, use_cache: bool = True, *_, **__) -> None:
        self._check_for_api()

        response = self.api.get_items(self.url, kind=RemoteObjectType.PLAYLIST, use_cache=use_cache)[0]
        if extend_tracks:
            tracks = [track["track"] for track in response["tracks"]["items"]]
            self.api.get_tracks_extra(tracks, limit=response["tracks"]["limit"], features=True, use_cache=use_cache)

        self.__init__(response=response, api=self.api)

    def _get_track_uris_from_api_response(self) -> list[str]:
        return [track["track"]["uri"] for track in self.response["tracks"]["items"]]


class SpotifyAlbum(RemoteAlbum[SpotifyTrack], SpotifyCollectionLoader[SpotifyTrack]):
    """
    Extracts key ``album`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    __slots__ = ("_tracks", "_artists")

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

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None):
        super().__init__(response=response, api=api)

        album_only = copy(response)
        album_only.pop("tracks", None)
        for track in response.get("tracks", {}).get("items", []):
            track["album"] = album_only

        self._artists = list(map(SpotifyArtist, response.get("artists", [])))
        self._tracks = list(map(SpotifyTrack, response.get("tracks", {}).get("items", [])))
        self._check_total()

        for track in self.tracks:
            track.disc_total = self.disc_total

    def reload(
            self, extend_artists: bool = True, extend_tracks: bool = True, use_cache: bool = True, *_, **__
    ) -> None:
        self._check_for_api()

        response = self.api.get_items(self.url, kind=RemoteObjectType.ALBUM, use_cache=use_cache)[0]
        if extend_artists:
            self.api.get_items(response["artists"], kind=RemoteObjectType.ARTIST, use_cache=use_cache)
        if extend_tracks:
            tracks = response["tracks"]
            self.api.get_tracks_extra(tracks["items"], limit=tracks["limit"], features=True, use_cache=use_cache)

        self.__init__(response=response, api=self.api)


class SpotifyArtist(RemoteArtist[SpotifyAlbum], SpotifyCollectionLoader[SpotifyAlbum]):
    """Extracts key ``artist`` data from a Spotify API JSON response."""

    __slots__ = ("_albums",)

    @staticmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        if isinstance(items, Iterable):
            return all(isinstance(item, SpotifyAlbum) for item in items)
        return isinstance(items, SpotifyAlbum)

    @property
    def name(self):
        return self.artist

    @property
    def items(self) -> list[SpotifyAlbum]:
        """The albums this artist is featured on"""
        return self._albums

    @property
    def artist(self):
        return self.response["name"]

    @property
    def albums(self) -> list[SpotifyAlbum]:
        album_frequencies = [
            (album, sum(artist.name == self.name for track in album for artist in track.artists))
            for album in self._albums
        ]
        return [album for album, _ in sorted(album_frequencies, key=lambda x: x[1])]

    @property
    def genres(self):
        return self.response.get("genres")

    @property
    def image_links(self):
        images = {image["height"]: image["url"] for image in self.response.get("images", [])}
        return {"cover_front": url for height, url in images.items() if height == max(images)}

    @property
    def rating(self):
        return self.response.get("popularity")

    @property
    def followers(self) -> int | None:
        """The total number of followers for this artist"""
        return self.response.get("followers", {}).get("total")

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None):
        super().__init__(response=response, api=api)
        self._albums = list(map(SpotifyAlbum, response["albums"]["items"])) if "albums" in response else []

    # TODO: this currently overrides parent loader because parent loader is too 'tracks' specific
    #  see if this can be modified to take advantage of the item filtering logic in the parent loader
    @classmethod
    def load(
            cls,
            value: str | dict[str, Any],
            api: SpotifyAPI,
            extend_albums: bool = False,
            extend_tracks: bool = False,
            use_cache: bool = True,
            *_,
            **__
    ) -> Self:
        obj = cls.__new__(cls)
        obj.api = api

        # set a mock response with URL to load from
        id_ = cls.extract_ids(value)[0]
        obj.response = {
            "href": cls.convert(id_, kind=RemoteObjectType.ARTIST, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        }
        obj.reload(extend_albums=extend_albums, extend_tracks=extend_tracks, use_cache=use_cache)
        return obj

    def reload(
            self, extend_albums: bool = False, extend_tracks: bool = False, use_cache: bool = True, *_, **__
    ) -> None:
        self._check_for_api()

        response = self.api.handler.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad)
        if extend_albums:
            self.api.get_artist_albums(response, use_cache=use_cache)
        if extend_albums and extend_tracks:
            for album in response["albums"]["items"]:
                self.api.extend_items(album["tracks"], key="tracks", unit="albums",  use_cache=use_cache)

        self.__init__(response=response, api=self.api)
