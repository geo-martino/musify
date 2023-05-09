import re
from abc import ABCMeta
from typing import Optional, List, MutableMapping, Any, Mapping

from syncify.spotify import IDType, ItemType, __URL_API__
from syncify.spotify.endpoints.utilities import Utilities, InputItemTypeVar


class ItemTYpe:
    pass


class Collections(Utilities, metaclass=ABCMeta):
    url_log_width = 87

    coll_item_map = {
        ItemType.PLAYLIST.name: ItemType.TRACK.name.lower().rstrip("s") + "s",
        ItemType.ALBUM.name: ItemType.TRACK.name.lower().rstrip("s") + "s",
        ItemType.ARTIST.name: ItemType.ALBUM.name.lower().rstrip("s") + "s",
        ItemType.SHOW.name: ItemType.EPISODE.name.lower().rstrip("s") + "s",
    }
    
    def get_playlist_url(self, playlist: str) -> str:
        """
        Determine the type of the given ``playlist`` and return its API URL.
        If type cannot be determined, attempt to find the playlist in the
        list of the currently authenticated user's playlists.

        :param playlist: In URL/URI/ID form, or the name of one of the currently authenticated user's playlists.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when it does not recognise the type of the input ``items`` parameter.
        """
        try:
            return f"{self.convert(playlist, kind=ItemType.PLAYLIST, type_out=IDType.URL_API)}"
        except ValueError:
            playlists = {pl["name"]: pl["href"] for pl in self.get_user_collections(use_cache=False)}
            if playlist not in playlists:
                raise ValueError(f"Given playlist is not a valid URL/URI/ID "
                                 f"and name not found in user's playlists: {playlist}")
            return f"{playlists[playlist]}"

    ###########################################################################
    ## GET helpers: Generic methods for getting collections and their items
    ###########################################################################
    def _get_collection_results(
            self, url: str, params: Optional[Mapping[str, Any]] = None, key: str = "items", use_cache: bool = True,
    ) -> MutableMapping[str, Any]:
        """
        Get responses from a given ``url``.
        This function executes each URL request individually for each ID.
        The function requests each page of the collection returning a list of all items
        found across all pages for this URL.

        :param url: The base API URL endpoint for the required requests.
            IMPORTANT: This string must have a placeholder for an ``id_`` parameter to be added via ``format``.
        :param params: Extra parameters to add to each request.
        :param key: The key with a list to extend on each new page.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API response for the collection containing the collection's items under the given ``key``.
        """
        r = {'next': url.rstrip("/")}
        total = self.requests.get(r["next"], params=params | {"limit": 1}, use_cache=use_cache).get("total")
        limit = params.get("limit") if params is not None else 0

        i = 0
        result = {}
        while r.get("next"):
            i += 1
            log_str = f"{'GET':<7}: {r['next']:<{self.url_log_width}}"
            if total is not None and limit is not None:
                log_str += f" |{min(i * limit, total):>4}/{total:<4} {key}"
            self._logger.debug(log_str)

            r = self.requests.get(r["next"], params=params, use_cache=use_cache)
            if len(result) == 0:
                result = r
            else:
                result[key].extend(r[key])

        return result

    def _get_collection_results_many(
            self,
            url: str,
            id_list: List[str],
            params: Optional[Mapping[str, Any]] = None,
            key: str = "items",
            unit: Optional[str] = None,
            use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        Get responses from a given ``url`` adding an ID to each request from a given ``id_list``.
        This function executes each URL request individually for each ID.
        The function requests each page of the collection returning a list of all items
        found across all pages for each ID.

        :param url: The base API URL endpoint for the required requests.
            IMPORTANT: This string must have a placeholder for an ``id_`` parameter to be added via ``format``.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param key: The key with a list to extend on each new page.
        :param unit: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection containing the collection's items under the given ``key``.
        """
        if unit is None:
            unit = re.sub(r"[-_]+", " ", key) if key is not None else "items"
        unit = unit.lower().rstrip("s") + "s"
        url = url.rstrip("/")

        url_log = url.format(id_='')
        self._logger.debug(f"{'GET':<7}: {url_log:<{self.url_log_width}} | {unit.title()}:{len(id_list):>5}")

        if len(id_list) > 10:  # show progress bar for batches which may take a long time
            id_list = self._get_progress_bar(iterate=id_list, desc=f'Getting {unit}', unit=unit)

        def get_result(id_: str) -> MutableMapping[str, Any]:
            return self._get_collection_results(url=url.format(id_=id_), params=params, key=key, use_cache=use_cache)
        results: List[MutableMapping[str, Any]] = [get_result(id_) for id_ in id_list]

        self._logger.debug(f"{'DONE':<7}: {url_log:<{self.url_log_width}} | "
                           f"Retrieved data for {len(results):>3} {unit}")
        return results

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_user_collections(
            self,
            user: Optional[str] = None,
            kind: ItemType = ItemType.PLAYLIST,
            batch_size: int = 50,
            use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s`` - Get collections for a given user's playlists.
            If user is None,

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type if given string is ID.
            Spotify only supports ``PLAYLIST`` types for non-authenticated users.
        :param batch_size: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and the object's current ``batch_size_max``. Maximum=50.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection.
        :exception ValueError: Raised a user is given and the ``kind`` is not ``PLAYLIST``.
            Or when the given ``kind`` is not a valid collection.
        """
        if kind == ItemType.ARTIST or kind.name not in self.coll_item_map:
            raise ValueError(f"{kind.name.title()}s are not a valid user collection type")
        if kind != ItemType.PLAYLIST and user is not None:
            raise ValueError(f"Only able to retrieve {kind.name.lower()}s from the currently authenticated user")

        if user is None:
            url = f"{__URL_API__}/me/{kind.name.lower()}s"
        else:
            url = f"{self.convert(user, kind=ItemType.USER, type_out=IDType.URL_API)}/{kind.name.lower()}s"

        r = {'next': url}
        collections = []
        while r['next']:
            self._logger.debug(f"{'GET':<7}: {r['next']:<{self.url_log_width}}")
            r = self.requests.get(r['next'], params={'limit': self.limit_value(batch_size)}, use_cache=use_cache)
            collections.extend(r['items'])

        self._logger.debug(f"{'DONE':<7}: {url:<{self.url_log_width}} | "
                           f"Retrieved items for {len(collections):>3} {kind.name.lower()}s")

        return collections

    def get_collection_items(
            self,
            items: InputItemTypeVar,
            kind: Optional[ItemType] = None,
            batch_size: int = 50,
            use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s/...`` - Get all items from a given list of ``items``. Items may be:
            * A single string value.
            * A dictionary response from Spotify API represent some item.
            * A list of string values.
            * A list of dictionary responses from Spotify API represent some items.

        :param items: List of items representing a list os collections of some kind. See description.
            These items must all be of the same type of collection i.e. all playlists OR all shows etc.
        :param kind: Item type of the given collection.
            If None, function will attempt to determine the type of the given values
        :param batch_size: Size of each batch of items to request in a collection items request.
            This value will be limited to be between ``1`` and the object's current ``batch_size_max``. Maximum=50.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection containing the collections items under the ``items`` key.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when the given ``kind`` is not a valid collection.
        """
        if kind is None:
            kind = self.get_item_type_from_list(items)

        coll_item_map = {
            ItemType.PLAYLIST.name: "tracks",
            ItemType.ALBUM.name: "tracks",
            ItemType.ARTIST.name: "albums",
            ItemType.SHOW.name: "episodes"
        }

        if kind.name not in coll_item_map:
            raise ValueError(f"{kind.name.title()}s are not a valid collection type")

        id_list = self.extract_ids(items, kind=kind)
        url = f"{__URL_API__}/{kind.name.lower()}s/{{id_}}/{coll_item_map[kind.name]}"
        params = {"limit": self.limit_value(batch_size)}
        collections = self._get_collection_results_many(
            url=url, id_list=id_list, key="items", unit=kind.name, params=params, use_cache=use_cache
        )

        item_count = sum(len(coll["items"]) for coll in collections)
        self._logger.debug(f"Retrieved data for {item_count:>4} {coll_item_map[kind.name]} "
                           f"across {len(collections)} {kind.name.lower()}s")
        return collections

    ###########################################################################
    ## POST endpoints
    ###########################################################################
    def create_playlist(self, name: str, public: bool = True, collaborative: bool = False) -> str:
        """
        ``POST: /users/{user_id}/playlists`` - Create an empty playlist for the current user.

        :param name: Name of playlist to create.
        :param public: Set playlist availability as `public` if True and `private` if False.
        :param collaborative: Set playlist to collaborative i.e. other users may edit the playlist.
        :return: API URL for playlist.
        """
        url = f'{__URL_API__}/users/{self.user_id}/playlists'

        body = {
            "name": name,
            "description": "Generated using Syncify: https://github.com/jor-mar/syncify",
            "public": public,
            "collaborative": collaborative,
        }
        self._logger.debug(f"{'POST':<7}: {url:<{self.url_log_width}} | Body: {body}")
        playlist = self.requests.post(url, json=body, use_cache=False)['href']

        self._logger.debug(f"{'DONE':<7}: {url:<{self.url_log_width}} | Created playlist: '{name}' -> {playlist}")
        return playlist

    def add_to_playlist(self, playlist: str, items: List[str], limit: int = 50, skip_dupes: bool = True) -> int:
        """
        ``POST: /playlists/{playlist_id}/tracks`` - Add list of tracks to a given playlist.

        :param playlist: Playlist URL/URI/ID to add to OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to add.
        :param limit: Size of each batch of IDs to add. This value will be limited to be between ``1``
            and the object's current ``batch_size_max``. Maximum=50.
        :param skip_dupes: Skip duplicates.
        :return: The number of tracks added to the playlist.
        :exception ValueError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist)}/tracks"

        if len(items) == 0:
            self._logger.debug(f"SKIP: {url:<{self.url_log_width}} | No data given")
            return 0

        item_type = self.get_item_type_from_list(items)
        if item_type is not None and not item_type == ItemType.TRACK:
            item_str = "unknown" if item_type is None else item_type.name.lower() + "s"
            raise ValueError(f"Given items must all be track URLs/URIs/IDs, not {item_str}")

        uri_list = [self.convert(item, kind=ItemType.TRACK, type_out=IDType.URI) for item in items]
        if skip_dupes:  # skip tracks currently in playlist
            items_current = self._get_collection_results(url, params={"limit": limit}, use_cache=False)["items"]
            uris_current = [item['track']['uri'] for item in items_current]
            uri_list = [uri for uri in uri_list if uri not in uris_current]

        for uris in self.chunk_items(uri_list, size=limit):
            params = {'uris': ','.join(uris)}
            self._logger.debug(f"{'POST':<7}: {url:<{self.url_log_width}} | "
                               f"Adding {len(uris):>3} items | Params: {params}")
            self.requests.post(url, params=params)

        self._logger.debug(f"{'DONE':<7}: {url:<{self.url_log_width}} | "
                           f"Added {len(uri_list)} items to playlist: {url}")
        return len(uri_list)

    ###########################################################################
    ## DELETE endpoints
    ###########################################################################
    def delete_playlist(self, playlist: str) -> str:
        """
        ``DELETE: /playlists/{playlist_id}/followers`` - Unfollow a given playlist.
        WARNING: This function will destructively modify your Spotify playlists.

        :param playlist. Playlist URL/URI/ID to unfollow OR the name of the playlist in the current user's playlists.
        :return: API URL for playlist.
        """
        url = f"{self.get_playlist_url(playlist)}/followers"
        
        self._logger.debug(f"{'DELETE':<7}: {url:<{self.url_log_width}}")
        self.requests.delete(url)
        return url

    def clear_from_playlist(self, playlist: str, items: Optional[List[str]] = None, batch_size: int = 100) -> int:
        """
        ``DELETE: /playlists/{playlist_id}/tracks`` - Clear tracks from a given playlist.
        WARNING: This function can destructively modify your Spotify playlists.

        :param playlist: Playlist URL/URI/ID to clear OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to remove. If None, clear all songs from the playlist.
        :param batch_size: Size of each batch of IDs to clear in a single request.
            This value will be limited to be between ``1`` and the object's current ``batch_size_max``. Maximum=50.
        :return: The number of tracks cleared from the playlist.
        :exception ValueError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist)}/tracks"

        if items is not None:
            item_type = self.get_item_type_from_list(items)
            if item_type is not None and not item_type == ItemType.TRACK:
                item_str = "unknown" if item_type is None else item_type.name.lower() + "s"
                raise ValueError(f"Given items must all be track URLs/URIs/IDs, not {item_str}")

            uri_list = [self.convert(item, kind=ItemType.TRACK, type_out=IDType.URI) for item in items]
        else:
            items = self._get_collection_results(url, params={"limit": batch_size}, use_cache=False)["items"]
            uri_list = [item['track']['uri'] for item in items]

        self._logger.debug(f"{'DELETE':<7}: {url:<{self.url_log_width}} | Clearing {len(uri_list):>3} tracks")
        for uris in self.chunk_items(uri_list, size=batch_size):
            self.requests.delete(url, json={'tracks': [{'uri': uri for uri in uris}]})

        self._logger.debug(f"{'DONE':<7}: {url:<{self.url_log_width}} | Cleared  {len(uri_list):>3} tracks")
        return len(uri_list)
