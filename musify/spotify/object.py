"""
Implements all :py:mod:`Remote` object types for Spotify.
"""

from __future__ import annotations

from abc import ABCMeta
from collections.abc import Iterable, MutableMapping, Mapping
from copy import copy, deepcopy
from datetime import datetime
from typing import Any, Self

from musify.shared.remote.enum import RemoteObjectType, RemoteIDType
from musify.shared.remote.object import RemoteCollection, RemoteCollectionLoader, RemoteTrack
from musify.shared.remote.object import RemotePlaylist, RemoteAlbum, RemoteArtist
from musify.shared.types import UnitCollection
from musify.shared.utils import to_collection
from musify.spotify.api import SpotifyAPI
from musify.spotify.base import SpotifyObject, SpotifyItem
from musify.spotify.exception import SpotifyCollectionError
from musify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyItemWranglerMixin(SpotifyItem, SpotifyDataWrangler, metaclass=ABCMeta):
    """Mixin for :py:class:`SpotifyItem` and :py:class:`SpotifyDataWrangler`"""
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
        if "release_date" not in album:
            return
        values = album["release_date"].split("-")
        return int(values[0]) if len(values) >= 1 and values[0].isdigit() else None

    @property
    def month(self):
        album = self.response.get("album", {})
        if "release_date" not in album or "release_date_precision" not in album:
            return
        if album["release_date_precision"] in {"year"}:
            # release date is not precise to month, do not return month even if it exists in the value
            return
        values = album["release_date"].split("-")
        return int(values[1]) if len(values) >= 2 and values[1].isdigit() else None

    @property
    def day(self):
        album = self.response.get("album", {})
        if "release_date" not in album or "release_date_precision" not in album:
            return
        if album["release_date_precision"] in {"year", "month"}:
            # release date is not precise to day, do not return day even if it exists in the value
            return
        values = album["release_date"].split("-")
        return int(values[2]) if len(values) >= 3 and values[2].isdigit() else None

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
        if isinstance(self.response["duration_ms"], Mapping):
            return self.response["duration_ms"]["totalMilliseconds"] / 1000
        return self.response["duration_ms"] / 1000

    @property
    def rating(self):
        return self.response.get("popularity")

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None, skip_checks: bool = False):
        self._disc_total = None
        self._comments = None
        self._artists: list[SpotifyArtist] | None = None

        if "track" in response and isinstance(response["track"], dict):
            # happens in 'user's saved ...' or playlist responses
            response = response["track"]

        super().__init__(response=response, api=api, skip_checks=skip_checks)

    def refresh(self, skip_checks: bool = False) -> None:
        self._artists = [
            SpotifyArtist(artist, api=self.api, skip_checks=skip_checks)
            for artist in self._response.get("artists", {})
        ]

    @classmethod
    def load(
            cls,
            value: str | dict[str, Any],
            api: SpotifyAPI,
            features: bool = False,
            analysis: bool = False,
            extend_album: bool = False,
            extend_artists: bool = False,
            use_cache: bool = True,
            *_,
            **__
    ) -> Self:
        obj = cls.__new__(cls)
        obj.api = api

        # set a mock response with URL to load from
        id_ = cls.extract_ids(value)[0]
        obj._response = {
            "href": cls.convert(id_, kind=RemoteObjectType.TRACK, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        }
        obj.reload(
            features=features,
            analysis=analysis,
            extend_album=extend_album,
            extend_artists=extend_artists,
            use_cache=use_cache
        )
        return obj

    def reload(
            self,
            features: bool = False,
            analysis: bool = False,
            extend_album: bool = False,
            extend_artists: bool = False,
            use_cache: bool = True,
            *_,
            **__
    ) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.handler.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        if extend_album:
            self.api.get_items(response["album"], kind=RemoteObjectType.ALBUM, extend=False, use_cache=use_cache)
        if extend_artists:
            self.api.get_items(response["artists"], kind=RemoteObjectType.ARTIST, use_cache=use_cache)
        if features or analysis:
            self.api.get_tracks_extra(response, features=features, analysis=analysis, use_cache=use_cache)

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
            leave_bar: bool = True,
            *args,
            **kwargs
    ) -> Self:
        unit = cls.__name__.removeprefix("Spotify").lower()
        kind = RemoteObjectType.from_name(unit)[0]
        key = api.collection_item_map[kind].name.lower() + "s"

        # no items given, regenerate API response from the URL
        if not items or (isinstance(value, Mapping) and (key not in value or api.items_key not in value[key])):
            if kind == RemoteObjectType.PLAYLIST:
                value = api.get_playlist_url(value)

            obj = cls.__new__(cls)
            obj.api = api
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
            response[key],
            kind=kind,
            key=api.collection_item_map[kind],
            use_cache=use_cache,
            leave_bar=leave_bar
        )
        if extend_tracks:
            if kind == RemoteObjectType.PLAYLIST:
                extend_response = [item["track"] for item in extend_response]
            api.get_tracks_extra(extend_response, limit=response[key]["limit"], features=True, use_cache=use_cache)

        return cls(response=response, api=api, skip_checks=False)


class SpotifyPlaylist(RemotePlaylist[SpotifyTrack], SpotifyCollectionLoader[SpotifyTrack]):
    """
    Extracts key ``playlist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    __slots__ = ("_tracks",)
    __attributes_ignore__ = "date_added"

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
        return int(self.response["followers"]["total"])

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

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None, skip_checks: bool = False):
        self._tracks: list[SpotifyTrack] | None = None
        super().__init__(response=response, api=api, skip_checks=skip_checks)

    def refresh(self, skip_checks: bool = False) -> None:
        self._tracks = [
            SpotifyTrack(track, api=self.api, skip_checks=skip_checks)
            for track in self._response.get("tracks", {}).get("items", [])
        ]
        if not skip_checks:
            self._check_total()

    def reload(self, extend_tracks: bool = False, use_cache: bool = True, *_, **__) -> None:
        self._check_for_api()

        response = self.api.get_items(self.url, kind=RemoteObjectType.PLAYLIST, use_cache=use_cache)[0]
        if extend_tracks:
            tracks = [track["track"] for track in response["tracks"]["items"]]
            self.api.get_tracks_extra(tracks, limit=response["tracks"]["limit"], features=True, use_cache=use_cache)

        self.__init__(response=response, api=self.api, skip_checks=not extend_tracks)

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
        values = self.response["release_date"].split("-")
        return int(values[0]) if len(values) >= 1 and values[0].isdigit() else None

    @property
    def month(self):
        if self.response["release_date_precision"] in {"year"}:
            # release date is not precise to month, do not return month even if it exists in the value
            return
        values = self.response["release_date"].split("-")
        return int(values[1]) if len(values) >= 2 and values[1].isdigit() else None

    @property
    def day(self):
        if self.response["release_date_precision"] in {"year", "month"}:
            # release date is not precise to day, do not return day even if it exists in the value
            return
        values = self.response["release_date"].split("-")
        return int(values[2]) if len(values) >= 3 and values[2].isdigit() else None

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

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None, skip_checks: bool = False):
        self._artists: list[SpotifyArtist] | None = None
        self._tracks: list[SpotifyTrack] | None = None

        if "album" in response and isinstance(response["album"], dict):
            # happens in 'user's saved ...' or playlist responses
            response = response["album"]

        super().__init__(response=response, api=api, skip_checks=skip_checks)

    def refresh(self, skip_checks: bool = False) -> None:
        album_only = copy(self.response)
        album_only.pop("tracks", None)
        for track in self.response.get("tracks", {}).get("items", []):
            track["album"] = album_only

        self._artists = [SpotifyArtist(artist, api=self.api) for artist in self._response.get("artists", {})]
        self._tracks = [
            SpotifyTrack(artist, api=self.api) for artist in self.response.get("tracks", {}).get("items", [])
        ]
        if not skip_checks:
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

        self.__init__(response=response, api=self.api, skip_checks=not extend_tracks)


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
        rating = self.response.get("popularity")
        return int(rating) if rating is not None else None

    @property
    def followers(self) -> int | None:
        """The total number of followers for this artist"""
        followers = self.response.get("followers", {}).get("total")
        return int(followers) if followers else None

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None, skip_checks: bool = False):
        self._albums: list[SpotifyAlbum] | None = None
        super().__init__(response=response, api=api, skip_checks=skip_checks)

    def refresh(self, skip_checks: bool = False) -> None:
        self._albums = [
            SpotifyAlbum(album, api=self.api, skip_checks=skip_checks)
            for album in self.response.get("albums", {}).get("items", [])
        ]

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
        obj._response = {
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
            kind = RemoteObjectType.ALBUM
            key = self.api.collection_item_map[kind]
            for album in response["albums"]["items"]:
                self.api.extend_items(album["tracks"], kind=kind, key=key, use_cache=use_cache)

        self.__init__(response=response, api=self.api, skip_checks=extend_albums and not extend_tracks)
