from abc import ABCMeta
from typing import Any, List, Mapping, MutableMapping, Optional, Union

from syncify.spotify import __URL_API__, IDType, ItemType
from syncify.spotify.api.utilities import InputItemTypeVar, Utilities


class ItemTYpe:
    pass


class Collections(Utilities, metaclass=ABCMeta):
    """Spotify API endpoints for processing collections i.e. playlists, albums, shows, and audiobooks"""

    items_key = "items"
    collection_types = {
        ItemType.PLAYLIST.name: ItemType.TRACK.name.lower().rstrip("s") + "s",
        ItemType.ALBUM.name: ItemType.TRACK.name.lower().rstrip("s") + "s",
        ItemType.AUDIOBOOK.name: ItemType.CHAPTER.name.lower().rstrip("s") + "s",
        ItemType.SHOW.name: ItemType.EPISODE.name.lower().rstrip("s") + "s",
    }
    
    def get_playlist_url(self, playlist: str, use_cache: bool = True) -> str:
        """
        Determine the type of the given ``playlist`` and return its API URL.
        If type cannot be determined, attempt to find the playlist in the
        list of the currently authenticated user's playlists.

        :param playlist: In URL/URI/ID form, or the name of one of the currently authenticated user's playlists.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when it does not recognise the type of the input ``items`` parameter.
        """
        try:
            return self.convert(playlist, kind=ItemType.PLAYLIST, type_out=IDType.URL)
        except ValueError:
            playlists = {pl["name"]: pl["href"] for pl in self.get_collections_user(use_cache=use_cache)}
            if playlist not in playlists:
                raise ValueError(f"Given playlist is not a valid URL/URI/ID "
                                 f"and name not found in user's playlists: {playlist}")
            return playlists[playlist]

    ###########################################################################
    ## GET helpers: Generic methods for getting collections and their items
    ###########################################################################
    def _get_collection_items(
            self, url: Union[str, Mapping[str, Any]], kind: Optional[ItemType] = None, use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        Get responses from a given ``url``.
        The function requests each page of the collection returning a list of all items
        found across all pages for this URL.

        The input ``url`` may either be a URL string, or a Spotify API JSON response for an items type endpoint
        which includes a required ``next`` key plus optional keys ``total``, ``limit``, ``items`` etc.

        If a JSON response is given, this updates the value of the ``items`` key by extending the ``items``
        with new results.

        :param url: The URL for the required requests, or a Spotify API JSON response for an items type endpoint.
        :param kind: Item type of the given collection for logging purposes. If None, defaults to 'entries'.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item
        """
        response: Mapping[str, Any] = {"href": url, "next": url} if isinstance(url, str) else url
        unit = self.collection_types[kind.name] if kind else 'entries'

        i = 0
        results = []
        count = 0 if isinstance(url, str) else len(url[self.items_key])
        while response.get("next"):
            i += 1
            log = None
            if "limit" in response and "total" in response:
                log = [f"{min(count + response['limit'], response['total']):>4}/{response['total']:<4} {unit}"]
            response = self.get(response["next"], use_cache=use_cache, log_pad=93, log_extra=log)
            results.extend(response[self.items_key])
            count += len(response[self.items_key])

        if isinstance(url, dict) and isinstance(url.get(self.items_key), list):
            url[self.items_key].extend(results)

        return results

    @staticmethod
    def _enrich_collections_response(collections: List[MutableMapping[str, Any]], kind: ItemType) -> None:
        for collection in collections:
            if collection.get("type") is None:
                collection["type"] = kind.name.lower()

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_collections_user(
            self,
            user: Optional[str] = None,
            kind: ItemType = ItemType.PLAYLIST,
            limit: int = 50,
            use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s`` - Get collections for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type if given string is ID.
            Spotify only supports ``PLAYLIST`` types for non-authenticated users.
        :param limit: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and ``50``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection.
        :exception ValueError: Raised a user is given and the ``kind`` is not ``PLAYLIST``.
            Or when the given ``kind`` is not a valid collection.
        """
        if kind == ItemType.ARTIST or kind.name not in self.collection_types:
            raise ValueError(f"{kind.name.title()}s are not a valid user collection type")
        if kind != ItemType.PLAYLIST and user is not None:
            raise ValueError(f"Only able to retrieve {kind.name.lower()}s from the currently authenticated user")

        if user is None:
            url = f"{__URL_API__}/me/{kind.name.lower()}s"
        else:
            url = f"{self.convert(user, kind=ItemType.USER, type_out=IDType.URL)}/{kind.name.lower()}s"

        params = {"limit": self.limit_value(limit, ceil=50)}
        r = self.get(url, params=params, use_cache=use_cache, log_pad=69)
        self._get_collection_items(r, kind=kind, use_cache=use_cache)
        collections = r[self.items_key]

        self._enrich_collections_response(collections, kind=kind)
        self._logger.debug(f"{'DONE':<7}: {url:<69} | Retrieved {len(collections):>3} {kind.name.lower()}s")
        return collections

    def get_collections(
            self, items: InputItemTypeVar, kind: Optional[ItemType] = None, limit: int = 100, use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s/...`` - Get all items from a given list of ``items``. Items may be:
            * A single string value representing a URL/URI/ID.
            * A list of string values representing a URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection including some items under an ``items`` key.
            * A list of Spotify API JSON responses for a collection including some items under an ``items`` key.

        If JSON response/s are given, this updates the value of the ``items`` in-place
        by clearing and replacing its values.

        :param items: List of items representing a list os collections of some kind. See description.
            These items must all be of the same type of collection i.e. all playlists OR all shows etc.
        :param kind: Item type of the given collection.
            If None, function will attempt to determine the type of the given values
        :param limit: Size of each batch of items to request in a collection items request.
            This value will be limited to be between ``1`` and the object's current ``batch_size_max``. Maximum=50.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection containing the collections items under the ``items`` key.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when the given ``kind`` is not a valid collection.
        """
        if kind is None:
            kind = self.get_item_type(items)
        if kind.name not in self.collection_types:
            raise ValueError(f"{kind.name.title()}s are not a valid collection type")

        if kind == ItemType.PLAYLIST and isinstance(items, str):
            items = self.get_playlist_url(items, use_cache=use_cache).split("/")[-1]

        id_list = self.extract_ids(items, kind=kind)
        url = f"{__URL_API__}/{kind.name.lower()}s"
        params = {"limit": self.limit_value(limit, ceil=100)}

        collections = []
        for id_ in id_list:
            r = self.get(f"{url}/{id_}", params=params, use_cache=use_cache, log_pad=69)
            self._get_collection_items(r[self.collection_types[kind.name]], kind=kind, use_cache=use_cache)
            collections.append(r)

        self._enrich_collections_response(collections, kind=kind)

        item_count = sum(len(coll[self.collection_types[kind.name]][self.items_key]) for coll in collections)
        self._logger.debug(f"{'DONE':<7}: {url:<69} | "
                           f"Retrieved {item_count:>4} {self.collection_types[kind.name]} "
                           f"across {len(collections)} {kind.name.lower()}s")

        if isinstance(items, dict) and len(collections) == 1:
            items.clear()
            items.update(collections[0])
        elif isinstance(items, list) and all(isinstance(item, dict) for item in items):
            items.clear()
            items.extend(collections)

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
        playlist = self.post(url, json=body, use_cache=False, log_pad=69)['href']

        self._logger.debug(f"{'DONE':<7}: {url:<69} | Created playlist: '{name}' -> {playlist}")
        return playlist

    def add_to_playlist(self, playlist: str, items: List[str], limit: int = 50, skip_dupes: bool = True) -> int:
        """
        ``POST: /playlists/{playlist_id}/tracks`` - Add list of tracks to a given playlist.

        :param playlist: Playlist URL/URI/ID to add to OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to add.
        :param limit: Size of each batch of IDs to add. This value will be limited to be between ``1`` and ``50``.
        :param skip_dupes: Skip duplicates.
        :return: The number of tracks added to the playlist.
        :exception ValueError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        limit = self.limit_value(limit, ceil=50)

        if len(items) == 0:
            self._logger.debug(f"SKIP: {url:<46} | No data given")
            return 0

        self.validate_item_type(items, kind=ItemType.TRACK)

        uri_list = [self.convert(item, kind=ItemType.TRACK, type_out=IDType.URI) for item in items]
        if skip_dupes:  # skip tracks currently in playlist
            pl_current = self.get_collections(url, kind=ItemType.PLAYLIST, limit=limit, use_cache=False)[0]
            uris_current = [item['track']['uri'] for item in pl_current[self.items_key]]
            uri_list = [uri for uri in uri_list if uri not in uris_current]

        for uris in self.chunk_items(uri_list, size=limit):
            params = {'uris': ','.join(uris)}
            log = [f"Adding {len(uris):>3} items"]
            self.post(url, params=params, use_cache=False, log_pad=46, log_extra=log)

        self._logger.debug(f"{'DONE':<7}: {url:<46} |  Added {len(uri_list)} items to playlist: {url}")
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
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/followers"
        self.delete(url, use_cache=False, log_pad=46)
        return url

    def clear_from_playlist(self, playlist: str, items: Optional[List[str]] = None, limit: int = 100) -> int:
        """
        ``DELETE: /playlists/{playlist_id}/tracks`` - Clear tracks from a given playlist.
        WARNING: This function can destructively modify your Spotify playlists.

        :param playlist: Playlist URL/URI/ID to clear OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to remove. If None, clear all songs from the playlist.
        :param limit: Size of each batch of IDs to clear in a single request.
            This value will be limited to be between ``1`` and ``100``.
        :return: The number of tracks cleared from the playlist.
        :exception ValueError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        limit = self.limit_value(limit, ceil=50)

        if items is not None:
            self.validate_item_type(items, kind=ItemType.TRACK)
            uri_list = [self.convert(item, kind=ItemType.TRACK, type_out=IDType.URI) for item in items]
        else:
            pl_current = self.get_collections(url, kind=ItemType.PLAYLIST, use_cache=False)[0]
            uri_list = [item['track']['uri'] for item in pl_current[self.items_key]]

        for uris in self.chunk_items(uri_list, size=limit):
            body = {'tracks': [{'uri': uri for uri in uris}]}
            log = [f"Clearing {len(uri_list):>3} tracks"]
            self.delete(url, json=body, use_cache=False, log_pad=69, log_extra=log)

        self._logger.debug(f"{'DONE':<7}: {url:<69} | Cleared  {len(uri_list):>3} tracks")
        return len(uri_list)
