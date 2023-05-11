from copy import copy
from datetime import datetime
from typing import Any, List, MutableMapping, Optional, Self, Mapping

from syncify.spotify import ItemType, IDType
from syncify.spotify.api.utilities import InputItemTypeVar
from syncify.spotify.library.item import SpotifyTrack, SpotifyArtist
from syncify.spotify.library.response import SpotifyResponse


class SpotifyAlbum(SpotifyResponse):

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.artist: str = self._list_sep.join(artist["name"] for artist in response["artists"])
        self.album: str = response["name"]
        self.album_artist: str = self.artist
        self.track_total: int = response["total_tracks"]
        self.genres: List[str] = response["genres"]
        self.year: int = int(response["release_date"][:4])
        self.disc_total: int = 0
        self.compilation: bool = response['album_type'] == "compilation"
        self.comments: Optional[List[str]] = None

        images = {image["height"]: image["url"] for image in response["images"]}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.rating: int = response['popularity']

        album_only = copy(response)
        album_only.pop("tracks")
        for track in response["tracks"]["items"]:
            track["album"] = album_only

        self.artists = [SpotifyArtist(artist) for artist in response["artists"]]
        self.tracks = [SpotifyTrack(track) for track in response["tracks"]["items"]]
        self.disc_total = max(track.disc_number for track in self.tracks)

        for track in self.tracks:
            track.disc_total = self.disc_total

    @classmethod
    def load(cls, value: InputItemTypeVar, use_cache: bool = True, tracks: Optional[List[SpotifyTrack]] = None) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        kind = ItemType.ALBUM
        response: MutableMapping[str, Any] = cls.api.get_collections(value, kind=kind, use_cache=use_cache)[0]

        if not tracks:
            id_ = cls.api.extract_ids(value)[0]
            obj.url = cls.api.convert(id_, kind=kind, type_in=IDType.ID, type_out=IDType.URL)
            obj.reload(use_cache=use_cache)
        else:
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in tracks}
            uri_get: List[str] = []

            for i, track_raw in enumerate(response["tracks"]["items"]):
                track: SpotifyTrack = uri_tracks.get(track_raw["track"]["uri"])
                if track:
                    track_raw.clear()
                    track_raw.update(track.response)
                else:
                    uri_get.append(track_raw["uri"])

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


class SpotifyPlaylist(SpotifyResponse):

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.name: str = response["name"]
        self.description: str = response["description"]
        self.collaborative: bool = response["collaborative"]
        self.public: bool = response["public"]
        self.followers: int = response["followers"]["total"]
        self.track_total: int = response["tracks"]["total"]

        self.owner_name: str = response["owner"]["display_name"]
        self.owner_id: str = response["owner"]["id"]

        images = {image["height"]: image["url"] for image in response["images"]}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.length: float = 0.0
        self.date_created: Optional[datetime] = None
        self.date_modified: Optional[datetime] = None

        self.tracks = [SpotifyTrack(track["track"], track["added_at"]) for track in response["tracks"]["items"]]

        if len(self.tracks) > 0:
            self.length: float = sum(track.length for track in self.tracks)
            self.date_created: datetime = min(track.date_added for track in self.tracks)
            self.date_modified: datetime = max(track.date_added for track in self.tracks)

    @classmethod
    def load(cls, value: InputItemTypeVar, use_cache: bool = True, tracks: Optional[List[SpotifyTrack]] = None) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        response = cls.api.get_collections(value, kind=ItemType.PLAYLIST, use_cache=use_cache)[0]

        if not tracks:
            obj.url = cls.api.get_playlist_url(value)
            obj.reload(use_cache=use_cache)
        else:
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in tracks}
            uri_get: List[str] = []

            for i, track_raw in enumerate(response["tracks"]["items"]):
                track: SpotifyTrack = uri_tracks.get(track_raw["track"]["uri"])
                if track:
                    response["tracks"]["items"][i]["track"] = track.response
                else:
                    uri_get.append(track_raw["track"]["uri"])

            tracks_new = cls.api.get_items(uri_get, kind=ItemType.TRACK, use_cache=use_cache)
            cls.api.get_tracks_extra(tracks_new, features=True, use_cache=use_cache)
            uri_tracks: Mapping[str, Mapping[str, Any]] = {r["uri"]: r for r in tracks_new}

            for i, track_raw in enumerate(response["tracks"]["items"]):
                track: Mapping[str, Any] = uri_tracks.get(track_raw["track"]["uri"])
                if track:
                    response["tracks"]["items"][i]["track"] = track

            obj.__init__(response)

        return obj

    def reload(self, use_cache: bool = True) -> None:
        self._check_for_api()

        response = self.api.get_collections(self.url, kind=ItemType.PLAYLIST, use_cache=use_cache)[0]
        tracks = [track["track"] for track in response["tracks"]["items"]]
        self.api.get_items(tracks, kind=ItemType.TRACK, use_cache=use_cache)
        self.api.get_tracks_extra(tracks, features=True, use_cache=use_cache)

        for old, new in zip(response["tracks"]["items"], tracks):
            old["track"] = new
        self.__init__(response)
