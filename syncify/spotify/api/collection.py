from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, MutableMapping
from itertools import batched
from time import sleep
from typing import Any
from urllib.parse import urlparse, urlencode

from syncify.spotify.api import __URL_API__, APIMethodInputType
from syncify.spotify.api.basic import APIBase
from syncify.spotify.enums import IDType, ItemType
from syncify.spotify.exception import SpotifyIDTypeError, SpotifyItemTypeError
from syncify.spotify.utils import validate_item_type, convert, get_item_type, extract_ids
from syncify.utils.helpers import limit_value


class Collections(APIBase, metaclass=ABCMeta):
    """Spotify API endpoints for processing collections i.e. playlists, albums, shows, and audiobooks"""

    items_key = "items"
    collection_types = {
        ItemType.PLAYLIST.name: ItemType.TRACK.name.casefold().rstrip("s") + "s",
        ItemType.ALBUM.name: ItemType.TRACK.name.casefold().rstrip("s") + "s",
        ItemType.AUDIOBOOK.name: ItemType.CHAPTER.name.casefold().rstrip("s") + "s",
        ItemType.SHOW.name: ItemType.EPISODE.name.casefold().rstrip("s") + "s",
    }

    @property
    @abstractmethod
    def user_id(self) -> str | None:
        """ID of the currently authenticated used"""
        raise NotImplementedError

    def get_playlist_url(self, playlist: str, use_cache: bool = True) -> str:
        """
        Determine the type of the given ``playlist`` and return its API URL.
        If type cannot be determined, attempt to find the playlist in the
        list of the currently authenticated user's playlists.

        :param playlist: In URL/URI/ID form, or the name of one of the currently authenticated user's playlists.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :raises SpotifyIDTypeError: Raised when the function cannot determine the item type of the input ``playlist``.
            Or when it does not recognise the type of the input ``playlist`` parameter.
        """
        try:
            return convert(playlist, kind=ItemType.PLAYLIST, type_out=IDType.URL)
        except SpotifyIDTypeError:
            playlists = {pl["name"]: pl["href"] for pl in self.get_collections_user(use_cache=use_cache)}
            if playlist not in playlists:
                raise SpotifyIDTypeError(f"Given playlist is not a valid URL/URI/ID "
                                         f"and name not found in user's playlists", value=playlist)
            return playlists[playlist]

    ###########################################################################
    ## GET helpers: Generic methods for getting collections and their items
    ###########################################################################
    def _get_collection_items(
            self, url: str | Mapping[str, Any], kind: ItemType | None = None, use_cache: bool = True,
    ) -> list[Mapping[str, Any]]:
        """
        Get responses from a given ``url``.
        The function requests each page of the collection returning a list of all items
        found across all pages for this URL.

        The input ``url`` may either be:
            * A URL string
            * A Spotify API JSON response for an items type endpoint which includes a required 
            ``next`` key plus optional keys ``total``, ``limit``, ``items`` etc.

        If a JSON response is given, this updates the value of the ``items`` key in-place 
        by extending the ``items`` with new results.

        :param url: The URL for the required requests, or a Spotify API JSON response for an items type endpoint.
            See description for allowed value types.
        :param kind: Item type of the given collection for logging purposes. If None, defaults to 'entries'.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item
        """
        response: Mapping[str, Any] = {"href": url, "next": url} if isinstance(url, str) else url
        unit = self.collection_types[kind.name] if kind else 'entries'

        bar = None
        pages = 0
        if "limit" in response and "total" in response:  # check if progress bar needed
            pages = (response["total"] - len(response.get("items", []))) // response["limit"]
            if pages > 5:  # show progress bar for batches which may take a long time
                bar = self.get_progress_bar(total=pages, desc=f'Getting {unit}', unit="pages")

        # ISSUE: initial API response always gives items 0-100 no matter which limit given for some unknown reason
        # When limit is e.g. 50 (the max allowed value), the 'next' url is then ALWAYS {url}?offset=0&limit=50
        # This means items 50-100 will be added twice if extending the items by the response from the 'next' url
        # WORKAROUND: manually create a valid 'next' url when response given as input
        if isinstance(url, dict) and isinstance(url.get(self.items_key), (list, set)) and url.get("next"):
            url_parsed = urlparse(url['next'])
            params = {"offset": len(url[self.items_key]), "limit": url["limit"]}
            url['next'] = f"{url_parsed.scheme}://{url_parsed.netloc}{url_parsed.path}?{urlencode(params)}"

        i = 0
        results = []
        count = 0 if isinstance(url, str) else len(url[self.items_key])
        while response.get("next"):  # loop through each page
            i += 1
            log = None
            if "limit" in response and "total" in response:  # log the current page count
                log = [f"{min(count + response['limit'], response['total']):>6}/{response['total']:<6} {unit}"]

            response = self.get(response["next"], use_cache=use_cache, log_pad=95, log_extra=log)
            results.extend(response[self.items_key])
            count += len(response[self.items_key])

            if bar and i <= pages:  # update progress bar
                sleep(0.1)
                bar.update()

        if bar is not None:
            bar.close()

        # if API response was given on input, update it with new responses
        if isinstance(url, dict) and isinstance(url.get(self.items_key), (list, set)):
            url[self.items_key].extend(results)

        return results

    @staticmethod
    def _enrich_collections_response(collections: list[MutableMapping[str, Any]], kind: ItemType):
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
            kind: ItemType = ItemType.PLAYLIST,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[Mapping[str, Any]]:
        """
        ``GET: /{kind}s`` - Get collections for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type if given string is ID.
            Spotify only supports ``PLAYLIST`` types for non-authenticated users.
        :param limit: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and ``50``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection.
        :raises SpotifyIDTypeError: Raised when the input ``user`` does not represent a user URL/URI/ID.
        :raises SpotifyItemTypeError: Raised a user is given and the ``kind`` is not ``PLAYLIST``.
            Or when the given ``kind`` is not a valid collection.
        """
        if kind == ItemType.ARTIST or kind.name not in self.collection_types:
            raise SpotifyItemTypeError(f"{kind.name.title()}s are not a valid user collection type", kind=kind)
        if kind != ItemType.PLAYLIST and user is not None:
            raise SpotifyItemTypeError(f"Only able to retrieve {kind.name.casefold()}s "
                                       f"from the currently authenticated user", kind=kind)

        if user is not None:
            url = f"{convert(user, kind=ItemType.USER, type_out=IDType.URL)}/{kind.name.casefold()}s"
        else:
            url = f"{__URL_API__}/me/{kind.name.casefold()}s"

        # get response
        params = {"limit": limit_value(limit, ceil=50)}
        r = self.get(url, params=params, use_cache=use_cache, log_pad=71)
        self._get_collection_items(r, kind=kind, use_cache=use_cache)
        collections = r[self.items_key]

        # enrich response
        self._enrich_collections_response(collections, kind=kind)
        self.logger.debug(f"{'DONE':<7}: {url:<71} | Retrieved {len(collections):>6} {kind.name.casefold()}s")
        return collections

    def get_collections(
            self, values: APIMethodInputType, kind: ItemType | None = None, limit: int = 50, use_cache: bool = True,
    ) -> list[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s/...`` - Get all items from a given list of ``values``. Items may be:
            * A string representing a URL/URI/ID.
            * A collection of strings representing URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection including some items under an ``items`` key,
                a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.
            * A list of Spotify API JSON responses for a collection including some items under an ``items`` key,
                a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.

        If JSON response/s are given, this updates the value of the ``items`` in-place
        by clearing and replacing its values.

        :param values: The values representing some Spotify collection. See description for allowed value types.
            These items must all be of the same type of collection i.e. all playlists OR all shows etc.
        :param kind: Item type of the given collection.
            If None, function will attempt to determine the type of the given values
        :param limit: Size of each batch of items to request in a collection items request.
            This value will be limited to be between ``1`` and the object's current ``batch_size_max``. Maximum=50.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each collection containing the collections items under the ``items`` key.
        :raises SpotifyItemTypeError: Raised when the function cannot determine the item type of the input ``values``.
            Or when the given ``kind`` is not a valid collection.
        """
        if kind is None:  # determine kind if not given
            kind = get_item_type(values)
        if kind.name not in self.collection_types:
            raise SpotifyItemTypeError(f"{kind.name.title()}s are not a valid collection type", kind=kind)

        if kind == ItemType.PLAYLIST and isinstance(values, str):
            values = self.get_playlist_url(values, use_cache=use_cache)

        url = f"{__URL_API__}/{kind.name.casefold()}s"
        params = {"limit": limit_value(limit, ceil=50)}
        id_list = extract_ids(values, kind=kind)

        unit = kind.name.casefold() + "s"
        if len(id_list) > 5:  # show progress bar for collection batches which may take a long time
            id_list = self.get_progress_bar(iterable=id_list, desc=f'Getting {unit}', unit=unit)

        collections = []
        for id_ in id_list:  # get responses for each collection in batches
            r = self.get(f"{url}/{id_}", params=params, use_cache=use_cache, log_pad=71)
            self._get_collection_items(r[self.collection_types[kind.name]], kind=kind, use_cache=use_cache)
            collections.append(r)

        self._enrich_collections_response(collections, kind=kind)

        item_count = sum(len(coll[self.collection_types[kind.name]][self.items_key]) for coll in collections)
        self.logger.debug(f"{'DONE':<7}: {url:<71} | "
                          f"Retrieved {item_count:>6} {self.collection_types[kind.name]} "
                          f"across {len(collections):>5} {kind.name.casefold()}s")

        # if API response was given on input, update it with new responses
        if isinstance(values, dict) and len(collections) == 1:
            values.clear()
            values.update(collections[0])
        elif isinstance(values, (list, set)) and all(isinstance(item, dict) for item in values):
            values.clear()
            values.extend(collections)

        return collections

    ###########################################################################
    ## POST endpoints
    ###########################################################################
    def create_playlist(self, name: str, public: bool = True, collaborative: bool = False) -> str:
        """
        ``POST: /users/{user_id}/playlists`` - Create an empty playlist for the current user with the given name.

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
        playlist = self.post(url, json=body, log_pad=71)['href']

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Created playlist: '{name}' -> {playlist}")
        return playlist

    def add_to_playlist(self, playlist: str, items: list[str], limit: int = 50, skip_dupes: bool = True) -> int:
        """
        ``POST: /playlists/{playlist_id}/tracks`` - Add list of tracks to a given playlist.

        :param playlist: Playlist URL/URI/ID to add to OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to add.
        :param limit: Size of each batch of IDs to add. This value will be limited to be between ``1`` and ``50``.
        :param skip_dupes: Skip duplicates.
        :return: The number of tracks added to the playlist.
        :raises SpotifyIDTypeError: Raised when the input ``playlist`` does not represent a playlist URL/URI/ID.
        :raises SpotifyItemTypeError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        limit = limit_value(limit, ceil=50)

        if len(items) == 0:
            self.logger.debug(f"{'SKIP':<7}: {url:<43} | No data given")
            return 0

        validate_item_type(items, kind=ItemType.TRACK)

        uri_list = [convert(item, kind=ItemType.TRACK, type_out=IDType.URI) for item in items]
        if skip_dupes:  # skip tracks currently in playlist
            pl_current = self.get_collections(url, kind=ItemType.PLAYLIST, limit=limit, use_cache=False)[0]
            tracks = pl_current[self.collection_types[ItemType.PLAYLIST.name]][self.items_key]
            uris_current = [track['track']['uri'] for track in tracks]
            uri_list = [uri for uri in uri_list if uri not in uris_current]

        for uris in batched(uri_list, limit):  # add tracks in batches
            params = {'uris': ','.join(uris)}
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
        WARNING: This function will destructively modify your Spotify playlists.

        :param playlist. Playlist URL/URI/ID to unfollow OR the name of the playlist in the current user's playlists.
        :return: API URL for playlist.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/followers"
        self.delete(url, log_pad=43)
        return url

    def clear_from_playlist(self, playlist: str, items: list[str] | None = None, limit: int = 100) -> int:
        """
        ``DELETE: /playlists/{playlist_id}/tracks`` - Clear tracks from a given playlist.
        WARNING: This function can destructively modify your Spotify playlists.

        :param playlist: Playlist URL/URI/ID to clear OR the name of the playlist in the current user's playlists.
        :param items: List of URLs/URIs/IDs of the tracks to remove. If None, clear all songs from the playlist.
        :param limit: Size of each batch of IDs to clear in a single request.
            This value will be limited to be between ``1`` and ``100``.
        :return: The number of tracks cleared from the playlist.
        :raises SpotifyIDTypeError: Raised when the input ``playlist`` does not represent a playlist URL/URI/ID.
        :raises SpotifyItemTypeError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        limit = limit_value(limit, ceil=100)

        if items is not None and len(items) == 0:
            return 0
        elif items is not None:  # clear only the items given
            validate_item_type(items, kind=ItemType.TRACK)
            uri_list = [convert(item, kind=ItemType.TRACK, type_out=IDType.URI) for item in items]
        else:  # clear everything
            pl_current = self.get_collections(url, kind=ItemType.PLAYLIST, use_cache=False)[0]
            tracks = pl_current[self.collection_types[ItemType.PLAYLIST.name]][self.items_key]
            uri_list = [track['track']['uri'] for track in tracks]

        if not uri_list:  # skip when nothing to clear
            return 0

        for uris in batched(uri_list, limit):  # clear in batches
            body = {'tracks': [{'uri': uri} for uri in uris]}
            log = [f"Clearing {len(uri_list):>3} tracks"]
            self.delete(url, json=body, log_pad=71, log_extra=log)

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Cleared  {len(uri_list):>3} tracks")
        return len(uri_list)
