from collections.abc import Mapping, Iterable, MutableMapping
from datetime import datetime
from typing import Any, Self

from syncify.remote import APIMethodInputType
from syncify.remote.enums import RemoteObjectType
from syncify.remote.library.playlist import RemotePlaylist
from syncify.spotify.library.collection import SpotifyCollection
from syncify.spotify.library.item import SpotifyTrack


class SpotifyPlaylist(SpotifyCollection, RemotePlaylist[SpotifyTrack]):
    """
    Extracts key ``playlist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value: str | None):
        self._description = value

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
        return self._image_links

    @property
    def has_image(self):
        images = self.response.get("album", {}).get("images", [])
        return images is not None and len(images) > 0

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
        return self._date_added

    def __init__(self, response: MutableMapping[str, Any]):
        super().__init__(response=response)

        self._name: str = response["name"]
        self._description: str = response["description"]
        self.collaborative: bool = response["collaborative"]
        self.public: bool = response["public"]

        images = {image["height"]: image["url"] for image in response["images"]}
        self._image_links: dict[str, str] = {
            "cover_front": url for height, url in images.items() if height == max(images)
        }

        # URI: date item was added
        self._date_added: dict[str, datetime] = {
            track["track"]["uri"]: datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%S%z")
            for track in response["tracks"]["items"]
        }

        self._tracks = [SpotifyTrack(track["track"]) for track in response["tracks"]["items"]]

    @classmethod
    def load(
            cls, value: APIMethodInputType, use_cache: bool = True, items: Iterable[SpotifyTrack] = (), *_, **__
    ) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        response = cls._load_response(value, use_cache=use_cache)

        if not items:  # no items given, regenerate API response from the URL
            obj.response = {"href": cls.api.get_playlist_url(value)}
            obj.reload(use_cache=use_cache)
        else:  # attempt to find items for this playlist in the given items
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in items}
            uri_get: list[str] = []

            for i, track_raw in enumerate(response["tracks"]["items"]):
                # loop through the skeleton response for this playlist
                # find items that match from the given items
                track: SpotifyTrack = uri_tracks.get(track_raw["track"]["uri"])
                if track:  # replace the skeleton response with the response from the track
                    response["tracks"]["items"][i]["track"] = track.response
                elif not track_raw["is_local"]:  # add to get list
                    uri_get.append(track_raw["track"]["uri"])

            if len(uri_get) > 0:  # get remaining items
                tracks_new = cls.api.get_tracks(uri_get, features=True, use_cache=use_cache)
                uri_tracks: Mapping[str, Mapping[str, Any]] = {r["uri"]: r for r in tracks_new}

                for i, track_raw in enumerate(response["tracks"]["items"]):
                    track: Mapping[str, Any] = uri_tracks.get(track_raw["track"]["uri"])
                    if track:  # replace the skeleton response with the new response
                        response["tracks"]["items"][i]["track"] = track

            obj.__init__(response)

        return obj

    def reload(self, use_cache: bool = True) -> None:
        self._check_for_api()

        # reload with enriched data
        response = self.api.get_items(self.url, kind=RemoteObjectType.PLAYLIST, use_cache=use_cache)[0]
        tracks = [track["track"] for track in response["tracks"]["items"]]
        self.api.get_tracks(tracks, features=True, use_cache=use_cache)

        for old, new in zip(response["tracks"]["items"], tracks):
            old["track"] = new
        self.__init__(response)

    def _get_track_uris_from_api_response(self) -> set[str]:
        return {track["track"]["uri"] for track in self.response["tracks"]["items"]}
