from abc import ABCMeta
from collections.abc import MutableMapping, Collection, Iterable, Mapping
from itertools import batched
from time import sleep
from typing import Any
from urllib.parse import urlparse

from syncify import PROGRAM_NAME, PROGRAM_URL
from syncify.remote.api import RemoteAPI, APIMethodInputType
from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.remote.exception import RemoteIDTypeError, RemoteItemTypeError
from syncify.utils.helpers import limit_value


class SpotifyAPICollections(RemoteAPI, metaclass=ABCMeta):
    """API endpoints for processing collections i.e. playlists, albums, shows, and audiobooks"""

    items_key = "items"
    collection_item_map = {
        RemoteItemType.PLAYLIST: RemoteItemType.TRACK,
        RemoteItemType.ALBUM: RemoteItemType.TRACK,
        RemoteItemType.AUDIOBOOK: RemoteItemType.CHAPTER,
        RemoteItemType.SHOW: RemoteItemType.EPISODE,
    }

    def _get_items_unit(self, kind: RemoteItemType) -> str:
        """Returns the string-formatted items key for the given collection kind"""
        if kind in [RemoteItemType.TRACK, RemoteItemType.EPISODE]:
            return kind.name.casefold()
        return self.collection_item_map[kind].name.casefold()

    def get_playlist_url(self, playlist: str | Mapping[str, Any], use_cache: bool = True) -> str:
        """
        Determine the type of the given ``playlist`` and return its API URL.
        If type cannot be determined, attempt to find the playlist in the
        list of the currently authenticated user's playlists.

        :param playlist: One of the following to identify the playlist URL:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The playlist URL.
        :raise RemoteIDTypeError: Raised when the function cannot determine the item type of
            the input ``playlist``. Or when it does not recognise the type of the input ``playlist`` parameter.
        """
        if isinstance(playlist, Mapping):
            if "href" in playlist:
                return playlist["href"]
            elif "id" in playlist:
                return self.convert(
                    playlist["id"], kind=RemoteItemType.PLAYLIST, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL
                )
            elif "uri" in playlist:
                return self.convert(
                    playlist["uri"], kind=RemoteItemType.PLAYLIST, type_in=RemoteIDType.URI, type_out=RemoteIDType.URL
                )

        try:
            return self.convert(playlist, kind=RemoteItemType.PLAYLIST, type_out=RemoteIDType.URL)
        except RemoteIDTypeError:
            playlists = {pl["name"]: pl["href"] for pl in self.get_collections_user(use_cache=use_cache)}
            if playlist not in playlists:
                raise RemoteIDTypeError(
                    "Given playlist is not a valid URL/URI/ID and name not found in user's playlists",
                    value=playlist
                )
            return playlists[playlist]

    ###########################################################################
    ## GET helpers: Generic methods for getting collections and their items
    ###########################################################################
    def _extend_items(
            self, items_block: MutableMapping[str, Any], kind: RemoteItemType | None = None, use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Extend the items for a given ``items_block`` API response.
        The function requests each page of the collection returning a list of all items
        found across all pages for this URL.

        Updates the value of the ``items`` key in-place by extending the value of the ``items`` key with new results.

        :param items_block: A remote API JSON response for an items type endpoint which includes a required
            ``next`` key plus optional keys ``total``, ``limit``, ``items`` etc.
        :param kind: Item type of the given collection for logging purposes. If None, defaults to 'entries'.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item
        """
        if not kind:
            kind = RemoteItemType.from_name(urlparse(items_block["href"]).path.split("/")[-1].rstrip("s"))[0]
        unit = self._get_items_unit(kind) + "s"

        if self.items_key not in items_block:
            items_block[self.items_key] = []

        # enable progress bar for longer calls
        total = items_block["total"]
        # pages = (total - len(items_block[self.items_key])) // items_block["limit"]
        bar = self.get_progress_bar(total=total, desc=f"Getting {kind.name.lower()}", unit=unit)

        # TODO: check this assumption
        # ISSUE: Spotify ALWAYS gives the initial 'next' url as {url}?offset=0&limit={limit}
        # This means items 0-{limit} will be added twice if extending the items by the response from the 'next' url
        # WORKAROUND: manually create a valid 'next' url when response given as input
        # if isinstance(items_block.get(self.items_key), Collection) and items_block.get("next"):
        #     url_parsed = urlparse(items_block["next"])
        #     params = {"offset": len(items_block[self.items_key]), "limit": items_block["limit"]}
        #
        #     url_parts = list(url_parsed[:])
        #     url_parts[4] = urlencode(params)
        #     items_block["next"] = str(urlunparse(url_parts))

        response = items_block
        while response.get("next") and bar.n < total:  # loop through each page
            log_count = min(bar.n + response['limit'], response['total'])
            log = [f"{log_count:>6}/{response['total']:<6} {unit}"]

            response = self.get(response["next"], use_cache=use_cache, log_pad=95, log_extra=log)
            items_block[self.items_key].extend(response[self.items_key])

            sleep(0.1)
            bar.update(len(response[self.items_key]))

        if bar is not None:
            bar.close()

        return items_block[self.items_key]

    @staticmethod
    def _enrich_collections_response(collections: Iterable[MutableMapping[str, Any]], kind: RemoteItemType) -> None:
        """Add type to API collection response"""
        for collection in collections:
            if collection.get("type") is None:
                collection["type"] = kind.name.casefold()

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_collections_user(
            self,
            user: str | None = None,
            kind: RemoteItemType = RemoteItemType.PLAYLIST,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` - Get collections for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type if given string is ID.
            Spotify only supports ``PLAYLIST`` types for non-authenticated users.
        :param limit: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and ``50``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each collection.
        :raise RemoteIDTypeError: Raised when the input ``user`` does not represent a user URL/URI/ID.
        :raise RemoteItemTypeError: Raised a user is given and the ``kind`` is not ``PLAYLIST``.
            Or when the given ``kind`` is not a valid collection.
        """
        # input validation
        if kind not in {RemoteItemType.TRACK, RemoteItemType.EPISODE} and kind not in self.collection_item_map:
            raise RemoteItemTypeError(f"{kind.name.title()}s are not a valid user collection type", kind=kind)
        if kind != RemoteItemType.PLAYLIST and user is not None:
            raise RemoteItemTypeError(
                f"Only able to retrieve {kind.name.casefold()}s from the currently authenticated user",
                kind=kind
            )

        if user is not None:
            url = f"{self.convert(user, kind=RemoteItemType.USER, type_out=RemoteIDType.URL)}/{kind.name.casefold()}s"
        else:
            url = f"{self.api_url_base}/me/{kind.name.casefold()}s"

        # get response
        params = {"limit": limit_value(limit, floor=1, ceil=50)}
        initial = self.get(url, params=params, use_cache=use_cache, log_pad=71)
        results = self._extend_items(initial, kind=kind, use_cache=use_cache)

        # enrich response
        self._enrich_collections_response(results, kind=kind)
        self.logger.debug(f"{'DONE':<7}: {url:<71} | Retrieved {len(results):>6} {kind.name.casefold()}s")

        return results

    def get_collections(
            self, values: APIMethodInputType, kind: RemoteItemType | None = None, use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s/...`` - Get all items from a given list of ``values``. Items may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including some items under an ``items`` key,
                a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.
            * A MutableSequence of remote API JSON responses for a collection including:
                - some items under an ``items`` key,
                - a valid ID value under an ``id`` key,
                - a valid item type value under a ``type`` key if ``kind`` is None.

        If JSON response/s are given, this updates the value of the ``items`` in-place
        by clearing and replacing its values.

        :param values: The values representing some remote collection. See description for allowed value types.
            These items must all be of the same type of collection i.e. all playlists OR all shows etc.
        :param kind: Item type of the given collection.
            If None, function will attempt to determine the type of the given values
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each collection containing the collections items under the ``items`` key.
        :raise RemoteItemTypeError: Raised when the function cannot determine the item type of the
            input ``values``. Or when the given ``kind`` is not a valid collection.
        """
        # input validation
        if kind is None:  # determine kind if not given
            kind = self.get_item_type(values)
        if kind not in self.collection_item_map:
            raise RemoteItemTypeError(f"{kind.name.title()}s are not a valid collection type", kind=kind)
        self.validate_item_type(values, kind=kind)

        if kind == RemoteItemType.PLAYLIST and isinstance(values, str):
            values = self.get_playlist_url(values, use_cache=use_cache)

        url = f"{self.api_url_base}/{kind.name.casefold()}s"
        id_list = self.extract_ids(values, kind=kind)

        unit = kind.name.casefold() + "s"
        if len(id_list) > 5:  # show progress bar for collection batches which may take a long time
            id_list = self.get_progress_bar(iterable=id_list, desc=f"Getting {unit}", unit=unit)

        collections = []
        key = self._get_items_unit(kind) + "s"
        for id_ in id_list:  # get responses for each collection in batches
            response = self.get(f"{url}/{id_}", use_cache=use_cache, log_pad=71)
            if response[key]["next"]:
                self._extend_items(response[key], kind=kind, use_cache=use_cache)
            collections.append(response)

        self._enrich_collections_response(collections, kind=kind)

        item_count = sum(len(coll[key][self.items_key]) for coll in collections)
        self.logger.debug(
            f"{'DONE':<7}: {url:<71} | "
            f"Retrieved {item_count:>6} {key} across {len(collections):>5} {kind.name.casefold()}s"
        )
        self._merge_results_to_input(original=values, results=collections, ordered=True)

        return collections

    ###########################################################################
    ## POST endpoints
    ###########################################################################
    def create_playlist(self, name: str, public: bool = True, collaborative: bool = False, *_, **__) -> str:
        """
        ``POST: /users/{user_id}/playlists`` - Create an empty playlist for the current user with the given name.

        :param name: Name of playlist to create.
        :param public: Set playlist availability as `public` if True and `private` if False.
        :param collaborative: Set playlist to collaborative i.e. other users may edit the playlist.
        :return: API URL for playlist.
        """
        url = f"{self.api_url_base}/users/{self.user_id}/playlists"

        body = {
            "name": name,
            "description": f"Generated using {PROGRAM_NAME}: {PROGRAM_URL}",
            "public": public,
            "collaborative": collaborative,
        }
        playlist = self.post(url, json=body, log_pad=71)["href"]

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Created playlist: '{name}' -> {playlist}")
        return playlist

    def add_to_playlist(
            self, playlist: str | Mapping[str, Any], items: Collection[str], limit: int = 100, skip_dupes: bool = True
    ) -> int:
        """
        ``POST: /playlists/{playlist_id}/tracks`` - Add list of tracks to a given playlist.

        :param playlist: One of the following to identify the playlist to clear:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
        :param items: List of URLs/URIs/IDs of the tracks to add.
        :param limit: Size of each batch of IDs to add. This value will be limited to be between ``1`` and ``100``.
        :param skip_dupes: Skip duplicates.
        :return: The number of tracks added to the playlist.
        :raise RemoteIDTypeError: Raised when the input ``playlist`` does not represent
            a playlist URL/URI/ID.
        :raise RemoteItemTypeError: Raised when the item types of the input ``items``
            are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        limit = limit_value(limit, floor=1, ceil=100)

        if len(items) == 0:
            self.logger.debug(f"{'SKIP':<7}: {url:<43} | No data given")
            return 0

        self.validate_item_type(items, kind=RemoteItemType.TRACK)

        uri_list = [self.convert(item, kind=RemoteItemType.TRACK, type_out=RemoteIDType.URI) for item in items]
        if skip_dupes:  # skip tracks currently in playlist
            pl_current = self.get_collections(url, kind=RemoteItemType.PLAYLIST, use_cache=False)[0]
            pl_items_key = self._get_items_unit(RemoteItemType.PLAYLIST)
            tracks = pl_current[pl_items_key + "s"][self.items_key]
            uris_current = [track["track"]["uri"] for track in tracks]
            uri_list = [uri for uri in uri_list if uri not in uris_current]

        for uris in batched(uri_list, limit):  # add tracks in batches
            params = {"uris": ','.join(uris)}
            log = [f"Adding {len(uris):>6} items"]
            self.post(url, params=params, log_pad=71, log_extra=log)

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Added  {len(uri_list):>6} items to playlist: {url}")
        return len(uri_list)

    ###########################################################################
    ## DELETE endpoints
    ###########################################################################
    def delete_playlist(self, playlist: str) -> str:
        """
        ``DELETE: /playlists/{playlist_id}/followers`` - Unfollow a given playlist.
        WARNING: This function will destructively modify your remote playlists.

        :param playlist. Playlist URL/URI/ID to unfollow OR the name of the playlist in the current user's playlists.
        :return: API URL for playlist.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/followers"
        self.delete(url, log_pad=43)
        return url

    def clear_from_playlist(
            self, playlist: str | Mapping[str, Any], items: Collection[str] | None = None, limit: int = 100
    ) -> int:
        """
        ``DELETE: /playlists/{playlist_id}/tracks`` - Clear tracks from a given playlist.
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
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        limit = limit_value(limit, floor=1, ceil=100)

        if items is not None and len(items) == 0:
            return 0
        elif items is not None:  # clear only the items given
            self.validate_item_type(items, kind=RemoteItemType.TRACK)
            uri_list = [self.convert(item, kind=RemoteItemType.TRACK, type_out=RemoteIDType.URI) for item in items]
        else:  # clear everything
            pl_current = self.get_collections(url, kind=RemoteItemType.PLAYLIST, use_cache=False)[0]
            pl_items_key = self._get_items_unit(RemoteItemType.PLAYLIST)
            tracks = pl_current[pl_items_key + "s"][self.items_key]
            uri_list = [track[pl_items_key]["uri"] for track in tracks]

        if not uri_list:  # skip when nothing to clear
            return 0

        for uris in batched(uri_list, limit):  # clear in batches
            body = {"tracks": [{"uri": uri} for uri in uris]}
            log = [f"Clearing {len(uri_list):>3} tracks"]
            self.delete(url, json=body, log_pad=71, log_extra=log)

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Cleared  {len(uri_list):>3} tracks")
        return len(uri_list)
