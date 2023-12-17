from abc import ABCMeta, abstractmethod
from collections.abc import Collection, MutableMapping, Mapping
from typing import Any

from syncify.api import RequestHandler
from .base import APIMethodInputType
from .enums import RemoteIDType, RemoteItemType
from .processors.wrangle import RemoteDataWrangler


class RemoteAPI(RequestHandler, RemoteDataWrangler, metaclass=ABCMeta):
    """
    Collection of endpoints for a remote API.
    See :py:class:`RequestHandler` and :py:class:`APIAuthoriser`
    for more info on which params to pass to authorise and execute requests.

    :param handler_kwargs: The authorisation kwargs to be passed to :py:class:`APIAuthoriser`.
    """

    @property
    @abstractmethod
    def api_url_base(self) -> str:
        """The base URL for making calls to the remote API"""
        raise NotImplementedError

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

    def __init__(self, **handler_kwargs):
        handler_kwargs = {k: v for k, v in handler_kwargs.items() if k != "name"}
        super().__init__(name=self.remote_source, **handler_kwargs)
        self._user_data: dict[str, Any] = {}

    ###########################################################################
    ## Misc helpers
    ###########################################################################
    @staticmethod
    def _merge_results_to_input(
            original: APIMethodInputType, results: list[dict[str, Any]], ordered: bool = True
    ) -> None:
        """
        If API response type given on input, update with new results.
        Assumes on a one-to-one relationship between ``original`` and the list of ``results``.

        :param original: The original values given to the function.
        :param results: The new results from the API.
        :param ordered: When True, function assumes the order of items in ``original`` and ``results`` is the same.
            When False, the function will attempt to match each input value to each result by matching on
            the ``id`` key of each dictionary.
        """
        id_key = "id"

        if isinstance(original, MutableMapping):
            if not len(results) == 1:
                return

            original.clear()
            original |= results[0]
        elif not isinstance(original, Collection):
            return

        # process as lists
        valid_input_types = all(isinstance(item, MutableMapping) for item in original)
        valid_lengths = len(original) == len(results)
        if not valid_input_types or not valid_lengths:
            return

        if ordered:
            for item, res in zip(original, results):
                item.clear()
                item |= res
            return

        valid_keys_values = all(id_key in item for item in original)
        valid_keys_results = all(id_key in item for item in results)
        if not valid_keys_values or not valid_keys_results:
            return

        result_mapped = {r[id_key]: r for r in results if r}
        for item in original:
            item.clear()
            item |= result_mapped[item[id_key]]

    @staticmethod
    def _extend_input_with_results(
            original: APIMethodInputType, results: dict[str, list[dict[str, Any]]], ordered: bool = True
    ) -> None:
        """
        If API response type given on input, update with new results.
        Assumes on a one-to-one relationship between ``original`` and the values of the ``results`` dict.

        :param original: The original values given to the function.
        :param results: The new results from the API in the form {<key to update on ``original``>: [``results``]}.
        :param ordered: When True, function assumes the order of items in ``original``
            and values of ``results`` is the same.
            When False, the function will attempt to match each input value to each result by matching on
            the ``id`` key of each dictionary.
        """
        id_key = "id"

        if isinstance(original, MutableMapping):
            for key, result in results.items():
                original[key] = result[0]
            return

        elif not isinstance(original, Collection):
            return

        # process as lists
        valid_input_types = all(isinstance(item, MutableMapping) for item in original)
        valid_lengths = all(len(original) == len(result) for result in results.values())
        if not valid_input_types or not valid_lengths:
            return

        if ordered:
            for key, result in results.items():
                for item, res in zip(original, result):
                    item[key] = res
            return

        valid_keys_values = all(id_key in item for item in original)
        valid_keys_results = all(id_key in item for result in results.values() for item in result)
        if not valid_keys_values or not valid_keys_results:
            return

        for key, result in results.items():
            result_mapped = {r[id_key]: r for r in result if r}
            for item in original:
                item[key] = result_mapped[item[id_key]]

    def format_item_data(
            self, i: int, name: str, uri: str, length: float = 0, total: int = 1, max_width: int = 50
    ) -> str:
        """
        Pretty format item data for displaying to the user

        :param i: The position of this item in the collection.
        :param name: The name of the item.
        :param uri: The URI of the item.
        :param length: The duration of the item in seconds.
        :param total: The total number of items in the collection
        :param max_width: The maximum width to print names as. Any name lengths longer than this will be truncated.
        :return: The formatted string.
        """
        return (
            f"\t\33[92m{str(i).zfill(len(str(total)))} \33[0m- "
            f"\33[97m{self.align_and_truncate(name, max_width=max_width)} \33[0m| "
            f"\33[91m{str(int(length // 60)).zfill(2)}:{str(round(length % 60)).zfill(2)} \33[0m| "
            f"\33[93m{uri} \33[0m- "
            f"{self.convert(uri, type_in=RemoteIDType.URI, type_out=RemoteIDType.URL_EXT)}"
        )

    @abstractmethod
    def pretty_print_uris(
            self, value: str | None = None, kind: RemoteIDType | None = None, use_cache: bool = True
    ) -> None:
        """
        Diagnostic function. Print tracks from a given link in ``<track> - <title> | <URI> - <URL>`` format
        for a given URL/URI/ID.

        :param value: URL/URI/ID to print information for.
        :param kind: When an ID is provided, give the kind of ID this is here.
            If None and ID is given, user will be prompted to give the kind anyway.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
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
    ## Core - GET endpoints
    ###########################################################################
    @abstractmethod
    def get_self(self, update_user_data: bool = True) -> dict[str, Any]:
        """
        ``GET`` - Get API response for information on current user

        :param update_user_data: When True, update the ``_user_data`` stored in this API object."""
        raise NotImplementedError

    @abstractmethod
    def query(self, query: str, kind: RemoteItemType, limit: int = 10, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        ``GET`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The remote item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        raise NotImplementedError

    ###########################################################################
    ## Item - GET endpoints
    ###########################################################################
    @abstractmethod
    def get_items(
            self,
            values: APIMethodInputType,
            kind: RemoteItemType | None = None,
            limit: int = 50,
            extend: bool = True,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET`` - Get information for given list of ``values``. Items may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including some items under an ``items`` key,
                a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.
            * A MutableSequence of remote API JSON responses for a collection including:
                - some items under an ``items`` key,
                - a valid ID value under an ``id`` key,
                - a valid item type value under a ``type`` key if ``kind`` is None.

        If a JSON response is given, this replaces the ``items`` with the new results.

        :param values: The values representing some remote items. See description for allowed value types.
            These items must all be of the same type of item i.e. all tracks OR all artists etc.
        :param kind: Item type if given string is ID.
        :param limit: Size of batches to request.
        :param extend: When True and the given ``kind`` is a collection of items,
            extend the response to include all items in this collection.
       :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item.
        :raise RemoteItemTypeError: Raised when the function cannot determine the item type
            of the input ``values``. Or when it does not recognise the type of the input ``values`` parameter.
        """
        raise NotImplementedError

    @abstractmethod
    def get_user_items(
            self,
            user: str | None = None,
            kind: RemoteItemType = RemoteItemType.PLAYLIST,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET`` - Get saved items for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type to retrieve for the user.
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
    def get_tracks(
            self, values: APIMethodInputType, limit: int = 50, use_cache: bool = True, *args, **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Wrapper for :py:meth:`get_items` which only returns Track type responses.
        See :py:meth:`get_items` for more info.
        """
        raise NotImplementedError

    ###########################################################################
    ## Collection - POST endpoints
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
    def add_to_playlist(
            self, playlist: str | Mapping[str, Any], items: Collection[str], limit: int = 50, skip_dupes: bool = True
    ) -> int:
        """
        ``POST`` - Add list of tracks to a given playlist.

        :param playlist: One of the following to identify the playlist to clear:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
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
    ## Collection - DELETE endpoints
    ###########################################################################
    @abstractmethod
    def delete_playlist(self, playlist: str | Mapping[str, Any]) -> str:
        """
        ``DELETE`` - Unfollow/delete a given playlist.
        WARNING: This function will destructively modify your remote playlists.

        :param playlist: One of the following to identify the playlist to clear:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
        :return: API URL for playlist.
        """
        raise NotImplementedError

    @abstractmethod
    def clear_from_playlist(
            self, playlist: str | Mapping[str, Any], items: Collection[str] | None = None, limit: int = 100
    ) -> int:
        """
        ``DELETE`` - Clear tracks from a given playlist.
        WARNING: This function can destructively modify your remote playlists.

        :param playlist: One of the following to identify the playlist to clear:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
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
