from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, MutableMapping, Optional, Self, Mapping, Literal, Collection, Union

from syncify.abstract.item import Item
from syncify.abstract.collection import Playlist, ItemCollection
from syncify.abstract.misc import Result
from syncify.spotify import ItemType, APIMethodInputType
from syncify.spotify.base import Spotify
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.library.collection import SpotifyCollection


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
        """The name of this playlist"""
        return self._name

    @property
    def items(self) -> List[SpotifyTrack]:
        return self.tracks

    @property
    def tracks(self) -> List[SpotifyTrack]:
        return self._tracks

    @property
    def track_total(self) -> int:
        return self.response["tracks"]["total"]

    @property
    def date_created(self) -> Optional[datetime]:
        """datetime object representing when the first track was added to this playlist"""
        return min(self.date_added.values()) if self.date_added else None

    @property
    def date_modified(self) -> Optional[datetime]:
        """datetime object representing when a track was most recently added/removed"""
        return max(self.date_added.values()) if self.date_added else None

    @property
    def date_added(self) -> Mapping[str, datetime]:
        """A map of ``{URI: date}`` for each item for when that item was added to the playlist"""
        return self._date_added

    @property
    def followers(self) -> int:
        """The number of followers this playlist has"""
        return self.response["followers"]["total"]

    @property
    def owner_name(self) -> str:
        """The name of the owner of this playlist"""
        return self.response["owner"]["display_name"]

    @property
    def owner_id(self) -> str:
        """The ID of the owner of this playlist"""
        return self.response["owner"]["id"]

    @property
    def has_image(self) -> bool:
        """Does this playlist have an image"""
        images = self.response.get("album", {}).get("images", [])
        return images is not None and len(images) > 0

    def __init__(self, response: MutableMapping[str, Any]):
        Spotify.__init__(self, response)

        self._name: str = response["name"]
        self.description: str = response["description"]
        self.collaborative: bool = response["collaborative"]
        self.public: bool = response["public"]

        images = {image["height"]: image["url"] for image in response["images"]}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}

        # uri: date item was added
        self._date_added: Mapping[str, datetime] = {
            track["track"]["uri"]: datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%S%z")
            for track in response["tracks"]["items"]
        }

        self._tracks = [SpotifyTrack(track["track"]) for track in response["tracks"]["items"]]

    @classmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True,
             items: Optional[Collection[SpotifyTrack]] = None) -> Self:
        cls._check_for_api()
        obj = cls.__new__(cls)
        response = cls._load_response(value, use_cache=use_cache)

        if not items:  # no items given, regenerate API response from the URL
            obj.response = {"href": cls.api.get_playlist_url(value)}
            obj.reload(use_cache=use_cache)
        else:  # attempt to find items for this playlist in the given items
            uri_tracks: Mapping[str, SpotifyTrack] = {track.uri: track for track in items}
            uri_get: List[str] = []

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

    def reload(self, use_cache: bool = True):
        self._check_for_api()

        # reload with enriched data
        response = self.api.get_collections(self.url, kind=ItemType.PLAYLIST, use_cache=use_cache)[0]
        tracks = [track["track"] for track in response["tracks"]["items"]]
        self.api.get_tracks(tracks, features=True, use_cache=use_cache)

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

        obj = cls.__new__(cls)
        obj.__init__(cls.api.get(url))
        return obj

    def delete(self):
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

        if clear == "all":  # remove all items from the remote playlist on Spotify
            removed = self.api.clear_from_playlist(self.url)
            uris_add = uris_obj
            uris_unchanged = []
        elif clear == "extra":  # remove items not present in the current list from the remote playlist on Spotify
            uris_clear = [uri for uri in uris_remote if uri not in uris_obj]
            removed = self.api.clear_from_playlist(self.url, items=uris_clear)
            uris_unchanged = [uri for uri in uris_remote if uri in uris_obj]

        added = self.api.add_to_playlist(self.url, items=uris_add, skip_dupes=clear != "all")
        if reload:  # reload the current playlist object from remote
            self.reload(use_cache=False)

        return SyncResultSpotifyPlaylist(
            start=len(uris_remote),
            added=added,
            removed=removed,
            unchanged=len(set(uris_remote).intersection(set(uris_unchanged))),
            difference=len(self.tracks) - len(uris_remote),
            final=len(self.tracks)
        )
