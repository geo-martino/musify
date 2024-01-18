"""
Functionality relating to generic remote objects.

Implements core :py:class:`Item` and :py:class:`ItemCollection` classes for remote object types.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Self, Literal, Any

from musify.shared.api.exception import APIError
from musify.shared.core.base import Item
from musify.shared.core.collection import ItemCollection
from musify.shared.core.misc import Result
from musify.shared.core.object import Track, Album, Playlist, Artist
from musify.shared.exception import MusifyKeyError
from musify.shared.remote.api import RemoteAPI
from musify.shared.remote.base import RemoteObject, RemoteItem
from musify.shared.remote.enum import RemoteIDType
from musify.shared.remote.exception import RemoteIDTypeError, RemoteError
from musify.shared.remote.processors.wrangle import RemoteDataWrangler
from musify.shared.utils import get_most_common_values


class RemoteItemWranglerMixin[T: RemoteObject](RemoteItem, RemoteDataWrangler, metaclass=ABCMeta):
    """Mixin for :py:class:`RemoteItem` and :py:class:`RemoteDataWrangler`"""
    pass


class RemoteTrack(RemoteItemWranglerMixin, Track, metaclass=ABCMeta):
    """Extracts key ``track`` data from a remote API JSON response."""

    __attributes_classes__ = (Track, RemoteItem)


class RemoteCollection[T: RemoteObject](ItemCollection[T], RemoteDataWrangler, metaclass=ABCMeta):
    """Generic class for storing a collection of remote objects."""

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = ("items", "track_total", "_total")

    def __getitem__(self, __key: str | int | slice | Item | RemoteObject) -> T | list[T] | list[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI/ID/URL.
        If an :py:class:`Item` is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        If a :py:class:`RemoteObject` is given, the ID is extracted from this object
        and the matching RemoteObject from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri:
                raise MusifyKeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri
            key_type = RemoteIDType.URI
        elif isinstance(__key, RemoteObject):
            __key = __key.id
            key_type = RemoteIDType.ID
        else:  # determine the ID type
            try:
                return next(item for item in self.items if item.name == __key)
            except StopIteration:
                try:
                    key_type = self.get_id_type(__key)
                except RemoteIDTypeError:
                    raise MusifyKeyError(f"ID Type not recognised: '{__key}'")

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
                raise MusifyKeyError(f"ID Type not recognised: '{__key}'")
        except StopIteration:
            raise MusifyKeyError(f"No matching {key_type.name} found: '{__key}'")


class RemoteCollectionLoader[T: RemoteObject](RemoteObject, RemoteCollection[T], metaclass=ABCMeta):
    """Generic class for storing a collection of remote objects that can be loaded from an API response."""

    __attributes_classes__ = (RemoteObject, RemoteCollection)

    def __eq__(self, __collection: RemoteObject | ItemCollection | Iterable[T]):
        if isinstance(__collection, RemoteObject):
            return self.uri == __collection.uri
        return super().__eq__(__collection)

    @property
    @abstractmethod
    def _total(self) -> int:
        """The total expected items for this collection"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(
            cls,
            value: str | Mapping[str, Any],
            api: RemoteAPI,
            use_cache: bool = True,
            items: Iterable[T] = (),
            *args,
            **kwargs
    ) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        ``value`` may be:
            * A string representing a URL/URI/ID.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.

        :param value: The value representing some remote collection. See description for allowed value types.
        :param api: An authorised API object to load the object from.
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
        if self._total != len(self.items):
            raise RemoteError(
                "The total items available in the response does not equal the total item count for this collection. "
                "Make sure the given collection response contains the right number of item responses: "
                f"{self._total} != {len(self.items)}"
            )


@dataclass(frozen=True)
class SyncResultRemotePlaylist(Result):
    """Stores the results of a sync with a remote playlist."""
    #: The total number of tracks in the playlist before the sync.
    start: int
    #: The number of tracks added to the playlist.
    added: int
    #: The number of tracks removed from the playlist.
    removed: int
    #: The number of tracks that were in the playlist before and after the sync.
    unchanged: int
    #: The difference between the total number tracks in the playlist from before and after the sync.
    difference: int
    #: The total number of tracks in the playlist after the sync.
    final: int


PLAYLIST_SYNC_KINDS = Literal["new", "refresh", "sync"]


class RemotePlaylist[T: RemoteTrack](Playlist[T], RemoteCollectionLoader[T], metaclass=ABCMeta):
    """Extracts key ``playlist`` data from a remote API JSON response."""

    __attributes_classes__ = (Playlist, RemoteCollectionLoader)

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
        """A map of ``{<URI>: <date>}`` for each item for when that item was added to the playlist"""
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
    def create(cls, api: RemoteAPI, name: str, public: bool = True, collaborative: bool = False) -> Self:
        """
        Create an empty playlist for the current user with the given name
        and initialise and return a new RemotePlaylist object from this new playlist.

        :param api: An API object with authorised access to a remote User to create playlists for.
        :param name: Name of playlist to create.
        :param public: Set playlist availability as `public` if True and `private` if False.
        :param collaborative: Set playlist to collaborative i.e. other users may edit the playlist.
        :return: :py:class:`RemotePlaylist` object for the generated playlist.
        """
        url = api.create_playlist(name=name, public=public, collaborative=collaborative)
        return cls(response=api.handler.get(url), api=api)

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
            kind: PLAYLIST_SYNC_KINDS = "new",
            reload: bool = True,
            dry_run: bool = True,
    ) -> SyncResultRemotePlaylist:
        """
        Synchronise this playlist object's items with the remote playlist it is associated with.

        Sync options:
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

    def merge(self, playlist: Playlist[T]) -> None:
        raise NotImplementedError


class RemoteAlbum[T: RemoteTrack](Album[T], RemoteCollectionLoader[T], metaclass=ABCMeta):
    """Extracts key ``album`` data from a remote API JSON response."""

    __attributes_classes__ = (Album, RemoteCollectionLoader)

    @property
    def _total(self):
        return self.track_total

    @property
    @abstractmethod
    def artists(self) -> list[RemoteArtist[T]]:
        raise NotImplementedError


class RemoteArtist[T: RemoteTrack](Artist[T], RemoteCollectionLoader[T], metaclass=ABCMeta):
    """Extracts key ``artist`` data from a remote API JSON response."""

    __attributes_classes__ = (Artist, RemoteCollectionLoader)

    @property
    def _total(self):
        return 0

    @property
    def tracks(self) -> list[T]:
        return [track for album in self.albums for track in album]

    @property
    def artists(self):
        return get_most_common_values(artist.name for album in self.albums for artist in album.artists)

    @property
    @abstractmethod
    def albums(self) -> list[RemoteAlbum[T]]:
        raise NotImplementedError

    @property
    def track_total(self):
        return sum(album.track_total for album in self.albums)

    @property
    @abstractmethod
    def image_links(self) -> dict[str, str]:
        """The images associated with this artist in the form ``{<image name/type>: <image link>}``"""
        raise NotImplementedError

    @property
    def has_image(self) -> bool:
        """Does this artist have images associated with them"""
        return len(self.image_links) > 0

    @property
    def length(self):
        if self.albums and any(album.length for album in self.albums):
            return sum(album.length if album.length else 0 for album in self.albums)
