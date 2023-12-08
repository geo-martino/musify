from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from typing import Any

from syncify.remote.api import APIMethodInputType
from syncify.remote.api.base import RemoteAPIBase
from syncify.remote.enums import RemoteItemType


class RemoteAPICollections(RemoteAPIBase, metaclass=ABCMeta):
    """API endpoints for processing collections i.e. playlists, albums, shows, and audiobooks"""

    @property
    @abstractmethod
    def user_id(self) -> str | None:
        """ID of the currently authenticated user"""
        raise NotImplementedError

    @property
    @abstractmethod
    def user_name(self) -> str | None:
        """Name of the currently authenticated user"""
        raise NotImplementedError

    @abstractmethod
    def get_playlist_url(self, playlist: str, use_cache: bool = True) -> str:
        """
        Determine the type of the given ``playlist`` and return its API URL.
        If type cannot be determined, attempt to find the playlist in the
        list of the currently authenticated user's playlists.

        :param playlist: In URL/URI/ID form, or the name of one of the currently authenticated user's playlists.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The playlist URL.
        :raise RemoteIDTypeError: Raised when the function cannot determine the item type of
            the input ``playlist``. Or when it does not recognise the type of the input ``playlist`` parameter.
        """
        raise NotImplementedError

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    @abstractmethod
    def get_collections_user(
            self,
            user: str | None = None,
            kind: RemoteItemType = RemoteItemType.PLAYLIST,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET`` - Get collections for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type if given string is ID.
        :param limit: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and ``50``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each collection.
        :raise RemoteIDTypeError: Raised when the input ``user`` does not represent a user URL/URI/ID.
        :raise RemoteItemTypeError: Raised a user is given and the ``kind`` is not ``PLAYLIST``.
            Or when the given ``kind`` is not a valid collection.
        """
        raise NotImplementedError

    @abstractmethod
    def get_collections(
            self,
            values: APIMethodInputType,
            kind: RemoteItemType | None = None,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET`` - Get all items from a given list of ``values``. Items may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including some items under an ``items`` key,
            a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.
            * A MutableSequence of remote API JSON responses for a collection including:
                - some items under an ``items`` key,
                - a valid ID value under an ``id`` key,
                - and a valid item type value under a ``type`` key if ``kind`` is None.

        If JSON response/s are given, this updates the value of the ``items`` in-place
        by clearing and replacing its values.

        :param values: The values representing some remote collection. See description for allowed value types.
            These items must all be of the same type of collection i.e. all playlists OR all shows etc.
        :param kind: Item type of the given collection.
            If None, function will attempt to determine the type of the given values
        :param limit: Size of each batch of items to request in a collection items request.
            This value will be limited to be between ``1`` and the object's current ``batch_size_max``. Maximum=50.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each collection containing the collections items under the ``items`` key.
        :raise RemoteItemTypeError: Raised when the function cannot determine the item type of
            the input ``values``. Or when the given ``kind`` is not a valid collection.
        """
        raise NotImplementedError

    ###########################################################################
    ## POST endpoints
    ###########################################################################
    @abstractmethod
    def create_playlist(self, name: str, *args, **kwargs) -> str:
        """
        ``POST`` - Create an empty playlist for the current user with the given name.

        :param name: Name of playlist to create.
        :return: API URL for playlist.
        """
        raise NotImplementedError

    @abstractmethod
    def add_to_playlist(self, playlist: str, items: Collection[str], limit: int = 50, skip_dupes: bool = True) -> int:
        """
        ``POST`` - Add list of tracks to a given playlist.

        :param playlist: Playlist URL/URI/ID to add to OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to add.
        :param limit: Size of each batch of IDs to add. This value will be limited to be between ``1`` and ``50``.
        :param skip_dupes: Skip duplicates.
        :return: The number of tracks added to the playlist.
        :raise RemoteIDTypeError: Raised when the input ``playlist`` does not represent
            a playlist URL/URI/ID.
        :raise RemoteItemTypeError: Raised when the item types of the input ``items``
            are not all tracks or IDs.
        """
        raise NotImplementedError

    ###########################################################################
    ## DELETE endpoints
    ###########################################################################
    @abstractmethod
    def delete_playlist(self, playlist: str) -> str:
        """
        ``DELETE`` - Unfollow/delete a given playlist.
        WARNING: This function will destructively modify your remote playlists.

        :param playlist. Playlist URL/URI/ID to unfollow OR the name of the playlist in the current user's playlists.
        :return: API URL for playlist.
        """
        raise NotImplementedError

    @abstractmethod
    def clear_from_playlist(self, playlist: str, items: Collection[str] | None = None, limit: int = 100) -> int:
        """
        ``DELETE`` - Clear tracks from a given playlist.
        WARNING: This function can destructively modify your remote playlists.

        :param playlist: Playlist URL/URI/ID to clear OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to remove. If None, clear all songs from the playlist.
        :param limit: Size of each batch of IDs to clear in a single request.
            This value will be limited to be between ``1`` and ``100``.
        :return: The number of tracks cleared from the playlist.
        :raise RemoteIDTypeError: Raised when the input ``playlist`` does not represent
            a playlist URL/URI/ID.
        :raise RemoteItemTypeError: Raised when the item types of the input ``items``
            are not all tracks or IDs.
        """
        raise NotImplementedError
