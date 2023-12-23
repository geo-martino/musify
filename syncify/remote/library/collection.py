from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Self, Literal, Any

from syncify.abstract.collection import ItemCollection, Album, Playlist
from syncify.abstract.item import Item
from syncify.abstract.misc import Result
from syncify.api.exception import APIError
from syncify.remote.enums import RemoteIDType
from syncify.remote.exception import RemoteIDTypeError, RemoteError
from syncify.remote.library.item import RemoteTrack
from syncify.remote.library.object import RemoteObject
from syncify.remote.processors.wrangle import RemoteDataWrangler


class RemoteCollection[T: RemoteObject](ItemCollection[T], RemoteDataWrangler, metaclass=ABCMeta):
    """Generic class for storing a collection of remote objects."""

    def __getitem__(self, __key: str | int | slice | Item) -> T | list[T] | list[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI/ID/URL.
        If an item is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri or __key.uri is None:
                raise KeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri
            key_type = RemoteIDType.URI
        else:  # determine the ID type
            try:
                return next(item for item in self.items if item.name == __key)
            except StopIteration:
                try:
                    key_type = self.get_id_type(__key)
                except RemoteIDTypeError:
                    raise KeyError(f"ID Type not recognised: '{__key}'")

        try:  # get the item based on the ID type
            if key_type == RemoteIDType.URI:
                return next(item for item in self.items if item.uri == __key)
            elif key_type == RemoteIDType.ID:
                return next(item for item in self.items if item.uri.split(":")[2] == __key)
            elif key_type == RemoteIDType.URL:
                __key = self.convert(__key, type_in=RemoteIDType.URL, type_out=RemoteIDType.URI)
                return next(item for item in self.items if item.uri == __key)
            elif key_type == RemoteIDType.URL_EXT:
                __key = self.convert(__key, type_in=RemoteIDType.URL_EXT, type_out=RemoteIDType.URI)
                return next(item for item in self.items if item.uri == __key)
            else:
                raise KeyError(f"ID Type not recognised: '{__key}'")
        except StopIteration:
            raise KeyError(f"No matching {key_type.name} found: '{__key}'")


class RemoteCollectionLoader[T: RemoteObject](RemoteObject, RemoteCollection[T], metaclass=ABCMeta):
    """Generic class for storing a collection of remote objects that can be loaded from an API response."""

    check_total: bool = True

    @property
    @abstractmethod
    def _total(self) -> int:
        """The total expected items for this collection"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(
            cls, value: str | Mapping[str, Any], use_cache: bool = True, items: Iterable[T] = (), *args, **kwargs
    ) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        ``value`` may be:
            * A string representing a URL/URI/ID.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.

        :param value: The value representing some remote collection. See description for allowed value types.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :param items: Optionally, give a list of available items to build a response for this collection.
            In doing so, the method will first try to find the API responses for the items of this collection
            in the given list before calling the API for any items not found there.
            This helps reduce the number of API calls made on initialisation.
        """
        raise NotImplementedError

    def _check_total(self) -> None:
        """
        Checks the total tracks processed for this collection equal to the collection total, raise exception if not
        """
        if self.check_total and self._total != len(self.items):
            raise RemoteError(
                "The total items available in the response does not equal the total item count for this collection. "
                "Make sure the given collection response contains the right number of item responses: "
                f"{self._total} != {len(self.items)}"
            )


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


class RemotePlaylist[T: RemoteTrack](Playlist[T], RemoteCollectionLoader[T], metaclass=ABCMeta):
    """Extracts key ``playlist`` data from a remote API JSON response."""

    @property
    @abstractmethod
    def owner_id(self) -> str:
        """The ID of the owner of this playlist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def owner_name(self) -> str:
        """The name of the owner of this playlist"""
        raise NotImplementedError

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

    @property
    def _total(self):
        return self.track_total

    @property
    def writeable(self) -> bool:
        """Is this playlist writeable i.e. can this program modify it"""
        try:
            self._check_for_api()
        except APIError:
            return False
        return self.api.user_id == self.owner_id

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
        Unfollow/delete the current playlist and clear the stored response for this object.
        WARNING: This function will destructively modify your remote playlists.
        """
        self._check_for_api()

        self.api.delete_playlist(self.url)
        self.response.clear()

    def sync(
            self,
            items: Iterable[Item] = (),
            kind: Literal["new", "refresh", "sync"] = "new",
            reload: bool = True,
            dry_run: bool = True,
    ) -> SyncResultRemotePlaylist:
        """
        Synchronise this playlist object's items with the remote playlist it is associated with. Sync options:

        * 'new': Do not clear any items from the remote playlist and only add any tracks
            from this playlist object not currently in the remote playlist.
        * 'refresh': Clear all items from the remote playlist first, then add all items from this playlist object.
        * 'sync': Clear all items not currently in this object's items list, then add all tracks
            from this playlist object not currently in the remote playlist.

        :param items: Provide an item collection or list of items to synchronise to the remote playlist.
            Use the currently loaded ``tracks`` in this object if not given.
        :param kind: Sync option for the remote playlist. See description.
        :param reload: When True, once synchronisation is complete, reload this RemotePlaylist object
            to reflect the changes on the remote playlist if enabled. Skip if False.
        :param dry_run: Run function, but do not modify the remote playlists at all.
        :return: The results of the sync as a :py:class:`SyncResultRemotePlaylist` object.
        """
        if not self.writeable:
            raise RemoteError(f"Cannot write to this playlist: {self.name}")

        uri_initial = [track.uri for track in (items or self.tracks) if track.uri]
        uri_remote = self._get_track_uris_from_api_response()

        # default settings when only synchronising for new items
        uri_add = [uri for uri in uri_initial if uri not in uri_remote]
        uri_unchanged = uri_remote
        removed = 0

        # process the remote playlist. when dry_run, mock the results
        if kind == "refresh":  # remove all items from the remote playlist
            removed = self.api.clear_from_playlist(self.url) if not dry_run else len(uri_remote)
            uri_add = uri_initial
            uri_unchanged = []
        elif kind == "sync":  # remove items not present in the current list from the remote playlist
            uri_clear = [uri for uri in uri_remote if uri not in uri_initial]
            removed = self.api.clear_from_playlist(self.url, items=uri_clear) if not dry_run else len(uri_clear)
            uri_unchanged = [uri for uri in uri_remote if uri in uri_initial]

        added = len(uri_add)
        if not dry_run:
            added = self.api.add_to_playlist(self.url, items=uri_add, skip_dupes=kind != "refresh")
            if reload:  # reload the current playlist object from remote
                self.reload(use_cache=False)

        return SyncResultRemotePlaylist(
            start=len(uri_remote),
            added=added,
            removed=removed,
            unchanged=len(uri_unchanged),
            difference=len(self.tracks) - len(uri_remote) if not dry_run and reload else added - removed,
            final=len(self.tracks) if not dry_run and reload else len(uri_remote) + added - removed
        )

    @abstractmethod
    def _get_track_uris_from_api_response(self) -> list[str]:
        """
        Returns a list of URIs from the API response stored for this playlist
        Implementation of this method is needed for the :py:func:`sync` function.
        """
        raise NotImplementedError

    def merge(self, playlist: Playlist) -> None:
        raise NotImplementedError


class RemoteAlbum[T: RemoteTrack](Album[T], RemoteCollectionLoader[T], metaclass=ABCMeta):
    """Extracts key ``album`` data from a remote API JSON response."""

    @property
    def _total(self):
        return self.track_total
