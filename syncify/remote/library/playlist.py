from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Self, Literal

from syncify.abstract.collection import Playlist
from syncify.abstract.item import Item
from syncify.abstract.misc import Result
from syncify.remote.library.collection import RemoteCollection
from syncify.remote.library.item import RemoteTrack


@dataclass(frozen=True)
class SyncResultRemotePlaylist(Result):
    """
    Stores the results of a sync with a remote playlist

    :ivar start: The total number of tracks in the playlist before the sync.
    :ivar added: The number of tracks added to the playlist.
    :ivar removed: The number of tracks removed from the playlist.
    :ivar unchanged: The number of tracks that were in the playlist before and after the sync.
    :ivar difference: The difference between the total number tracks in the playlist from before and after the sync.
    :ivar final: The total number of tracks in the playlist after the sync.
    """
    start: int
    added: int
    removed: int
    unchanged: int
    difference: int
    final: int


class RemotePlaylist[T: RemoteTrack](RemoteCollection[T], Playlist[T], metaclass=ABCMeta):
    """Extracts key ``playlist`` data from a remote API JSON response."""

    @property
    def owner_id(self) -> str:
        """The ID of the owner of this playlist"""
        return self.response["owner"]["id"]

    @property
    def owner_name(self) -> str:
        """The name of the owner of this playlist"""
        return self.response["owner"]["display_name"]

    @property
    @abstractmethod
    def followers(self) -> int:
        """The number of followers this playlist has"""
        raise NotImplementedError

    @property
    @abstractmethod
    def date_added(self) -> dict[str, datetime]:
        """A map of ``{URI: date}`` for each item for when that item was added to the playlist"""
        raise NotImplementedError

    @classmethod
    def create(cls, name: str, public: bool = True, collaborative: bool = False) -> Self:
        """
        Create an empty playlist for the current user with the given name
        and initialise and return a new RemotePlaylist object from this new playlist.

        :param name: Name of playlist to create.
        :param public: Set playlist availability as `public` if True and `private` if False.
        :param collaborative: Set playlist to collaborative i.e. other users may edit the playlist.
        :return: :py:class:`RemotePlaylist` object for the generated playlist.
        """
        cls._check_for_api()

        url = cls.api.create_playlist(name=name, public=public, collaborative=collaborative)

        obj = cls.__new__(cls)
        obj.__init__(cls.api.get(url))
        return obj

    def delete(self) -> None:
        """
        Unfollow/delete the current playlist and clear all attributes from this object.
        WARNING: This function will destructively modify your remote playlists.
        """
        self._check_for_api()
        self.api.delete_playlist(self.url)
        for key in list(self.__dict__.keys()):
            delattr(self, key)

    def sync(
            self,
            items: Iterable[Item] = (),
            clear: Literal["all", "extra"] | None = None,
            reload: bool = True,
            dry_run: bool = False,
    ) -> SyncResultRemotePlaylist:
        """
        Synchronise this playlist object with the remote playlist it is associated with. Clear options:

        * None: Do not clear any items from the remote playlist and only add any tracks
            from this playlist object not currently in the remote playlist.
        * 'all': Clear all items from the remote playlist first, then add all items from this playlist object.
        * 'extra': Clear all items not currently in this object's items list, then add all tracks
            from this playlist object not currently in the remote playlist.

        :param items: Provide an item collection or list of items to synchronise to the remote playlist.
            Use the currently loaded ``tracks`` in this object if not given.
        :param clear: Clear option for the remote playlist. See description.
        :param reload: When True, once synchronisation is complete, reload this RemotePlaylist object
            to reflect the changes on the remote playlist if enabled. Skip if False.
        :param dry_run: Run function, but do not modify the remote playlists at all.
        :return: The results of the sync as a :py:class:`SyncResultRemotePlaylist` object.
        """
        self._check_for_api()

        uris_obj = {track.uri for track in (items if items else self.tracks) if track.uri}
        uris_remote = set(self._get_track_uris_from_api_response())

        uris_add = [uri for uri in uris_obj if uri not in uris_remote]
        uris_unchanged = uris_remote
        removed = 0

        # process the remote playlist. when dry_run, mock the results
        if clear == "all":  # remove all items from the remote playlist
            removed = self.api.clear_from_playlist(self.url) if not dry_run else len(uris_remote)
            uris_add = uris_obj
            uris_unchanged = set()
        elif clear == "extra":  # remove items not present in the current list from the remote playlist
            uris_clear = {uri for uri in uris_remote if uri not in uris_obj}
            removed = self.api.clear_from_playlist(self.url, items=uris_clear) if not dry_run else len(uris_clear)
            uris_unchanged = {uri for uri in uris_remote if uri in uris_obj}

        if not dry_run:
            added = self.api.add_to_playlist(self.url, items=uris_add, skip_dupes=clear != "all")
        else:
            added = len(uris_add) if clear != "all" else len(set(uris_add) - uris_remote)

        if not dry_run and reload:  # reload the current playlist object from remote
            self.reload(use_cache=False)

        return SyncResultRemotePlaylist(
            start=len(uris_remote),
            added=added,
            removed=removed,
            unchanged=len(set(uris_remote).intersection(uris_unchanged)),
            difference=len(self.tracks) - len(uris_remote),
            final=len(self.tracks)
        )

    @abstractmethod
    def _get_track_uris_from_api_response(self) -> set[str]:
        """
        Returns a list of URIs from the API response stored for this playlist
        Implementation of this method is needed for the :py:func:`sync` function.
        """
        raise NotImplementedError
