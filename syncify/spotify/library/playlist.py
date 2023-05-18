from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, MutableMapping, Optional, Self, Mapping, Literal, Collection, Union

from syncify.abstract import Item
from syncify.abstract.collection import Playlist, ItemCollection
from syncify.abstract.misc import Result
from syncify.spotify import ItemType
from syncify.spotify.api.utilities import APIMethodInputType
from syncify.spotify.library.collection import SpotifyCollection
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.library.response import SpotifyResponse


@dataclass
class SyncResultSpotifyPlaylist(Result):
    """Stores the results of a sync with a remote Spotify playlist"""
    start: int
    added: int
    removed: int
    unchanged: int
    difference: int
    final: int


class SpotifyPlaylist(Playlist, SpotifyCollection):
    """
    Extracts key ``playlist`` data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    @property
    def name(self) -> str:
        return self._name

    @property
    def items(self) -> List[SpotifyTrack]:
        return self.tracks

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self._name: str = response["name"]
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
    def load(cls, value: APIMethodInputType, use_cache: bool = True,
             items: Optional[Collection[SpotifyTrack]] = None) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        response = cls._load_response(value, use_cache=use_cache)

        if not items:
            obj.url = cls.api.get_playlist_url(value)
            obj.reload(use_cache=use_cache)
        else:
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in items}
            uri_get: List[str] = []

            for i, track_raw in enumerate(response["tracks"]["items"]):
                track: SpotifyTrack = uri_tracks.get(track_raw["track"]["uri"])
                if track:
                    response["tracks"]["items"][i]["track"] = track.response
                elif not track_raw["is_local"]:
                    uri_get.append(track_raw["track"]["uri"])

            if len(uri_get) > 0:
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

    @classmethod
    def create(cls, name: str, public: bool = True, collaborative: bool = False) -> Self:
        """
        Create an empty playlist for the current user with the given name
        and initialise and return a new SpotifyPlaylist object from this new playlist.

        :param name: Name of playlist to create.
        :param public: Set playlist availability as `public` if True and `private` if False.
        :param collaborative: Set playlist to collaborative i.e. other users may edit the playlist.
        :return: SpotifyPlaylist object for the generated playlist.
        """
        cls._check_for_api()

        url = cls.api.create_playlist(name=name, public=public, collaborative=collaborative)
        date_created = datetime.now()

        obj = cls.__new__(cls)
        obj.__init__(cls.api.get(url))
        obj.date_created = date_created
        obj.date_modified = date_created
        return obj

    def delete(self) -> None:
        """
        Unfollow the current playlist and clear all attributes from this object.
        WARNING: This function will destructively modify your Spotify playlists.
        """
        self._check_for_api()
        self.api.delete_playlist(self.url)
        for key in list(self.__dict__.keys()):
            delattr(self, key)

    def sync(
            self,
            items: Optional[Union[ItemCollection, List[Item]]] = None,
            clear: Optional[Literal['all', 'extra']] = None,
            reload: bool = True
    ) -> SyncResultSpotifyPlaylist:
        """
        Synchronise this playlist object with the remote Spotify playlist it is associated with. Clear options:

        * None: Do not clear any items from the remote playlist and only add any tracks
            from this playlist object not currently in the remote playlist.
        * 'all': Clear all items from the remote playlist first, then add all items from this playlist object.
        * 'extra': Clear all items not currently in this object's items list, then add all tracks
            from this playlist object not currently in the remote playlist.

        :param items: Provide an item collection or list of items to synchronise to the remote playlist.
            Use the currently loaded ``tracks`` in this object if not given.
        :param clear: Clear option for the remote playlist. See description.
        :param reload: When True, once synchronisation is complete, reload this SpotifyPlaylist object
            to reflect the changes on the remote playlist if enabled. Skip if False.
        :return: UpdateResult object with stats on the changes to the remote playlist.
        """
        self._check_for_api()

        uris_obj = [track.uri for track in (items if items else self.tracks) if track.uri]
        uris_remote = [track["track"]["uri"] for track in self.response["tracks"]["items"]]

        uris_add = [uri for uri in uris_obj if uri not in uris_remote]
        uris_unchanged = uris_remote
        removed = 0

        if clear == "all":
            removed = self.api.clear_from_playlist(self.url)
            uris_add = uris_obj
            uris_unchanged = []
        elif clear == "extra":
            uris_clear = [uri for uri in uris_remote if uri not in uris_obj]
            removed = self.api.clear_from_playlist(self.url, items=uris_clear)
            uris_unchanged = [uri for uri in uris_remote if uri in uris_obj]

        added = self.api.add_to_playlist(self.url, items=uris_add, skip_dupes=True)
        if reload:
            self.reload(use_cache=False)

        return SyncResultSpotifyPlaylist(
            start=len(uris_remote),
            added=added,
            removed=removed,
            unchanged=len(set(uris_remote).intersection(set(uris_unchanged))),
            difference=len(self.tracks) - len(uris_remote),
            final=len(self.tracks)
        )
