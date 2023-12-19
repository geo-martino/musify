import re
from abc import ABCMeta
from collections.abc import Collection, Mapping, MutableMapping
from itertools import batched
from time import sleep
from typing import Any

from syncify.api.exception import APIError
from syncify.remote.api import RemoteAPI, APIMethodInputType
from syncify.remote.enums import RemoteObjectType, RemoteIDType
from syncify.remote.exception import RemoteObjectTypeError
from syncify.utils.helpers import limit_value


class SpotifyAPIItems(RemoteAPI, metaclass=ABCMeta):

    items_key = "items"
    collection_item_map = {
        RemoteObjectType.PLAYLIST: RemoteObjectType.TRACK,
        RemoteObjectType.ALBUM: RemoteObjectType.TRACK,
        RemoteObjectType.AUDIOBOOK: RemoteObjectType.CHAPTER,
        RemoteObjectType.SHOW: RemoteObjectType.EPISODE,
    }
    user_item_types = (
            set(collection_item_map) | {RemoteObjectType.TRACK, RemoteObjectType.ARTIST, RemoteObjectType.EPISODE}
    )

    def _get_unit(self, key: str | None = None, unit: str | None = None) -> str:
        """Determine the unit type to use in the progress bar"""
        if unit is None:
            unit = re.sub(r"[-_]+", " ", key) if key is not None else self.items_key
        return unit.casefold().rstrip("s") + "s"

    ###########################################################################
    ## GET helpers: Generic methods for getting items
    ###########################################################################
    def _get_items_multi(
            self,
            url: str,
            id_list: Collection[str],
            params: Mapping[str, Any] | None = None,
            key: str | None = None,
            unit: str | None = None,
            use_cache: bool = True,
            *_,
            **__,
    ) -> list[dict[str, Any]]:
        """
        Get responses from a given ``url`` appending an ID to each request from a given ``id_list`` i.e. ``{URL}/{ID}``.
        This function executes each URL request individually for each ID i.e. ``url``/``id``.

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param key: The key to reference from each response to get the list of required values.
        :param unit: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item at the given ``key``.
        :raise APIError: When the given ``key`` is not in the API response.
        """
        url = url.rstrip("/")
        unit = self._get_unit(key=key, unit=unit)

        # prepare iterator
        if len(id_list) >= 50:  # show progress bar for batches which may take a long time
            id_list = self.get_progress_bar(iterable=id_list, desc=f"Getting {unit}", unit=unit)

        results: list[dict[str, Any]] = []
        log = [f"{unit.title()}:{len(id_list):>5}"]
        for id_ in id_list:
            response = self.get(f"{url}/{id_}", params=params, use_cache=use_cache, log_pad=43, log_extra=log)
            if key and key not in response:
                raise APIError(f"Given key '{key}' not found in response keys: {list(response.keys())}")

            results.extend(response[key]) if key else results.append(response)

        return results

    def _get_items_batched(
            self,
            url: str,
            id_list: Collection[str],
            params: Mapping[str, Any] | None = None,
            key: str | None = None,
            unit: str | None = None,
            limit: int = 50,
            use_cache: bool = True,
            *_,
            **__,
    ) -> list[dict[str, Any]]:
        """
        Get responses from a given ``url`` appending an ID to each request from a given ``id_list`` i.e. ``{URL}/{ID}``.
        This function executes each URL request in batches of IDs based on the given ``batch_size``.
        It passes this chunked list of IDs to the request handler as a set of params in the form:
        ``{'ids': '<comma separated string of IDs>'}``

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param key: The key to reference from each response to get the list of required values.
        :param unit: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :param limit: Size of each batch of IDs to get. This value will be limited to be between ``1`` and ``50``.
        :return: API JSON responses for each item at the given ``key``.
        :raise APIError: When the given ``key`` is not in the API response.
        """
        url = url.rstrip("/")
        unit = self._get_unit(key=key, unit=unit)

        # prepare iterator
        id_chunks = list(batched(id_list, limit_value(limit, floor=1, ceil=50)))
        bar = range(len(id_chunks))
        if len(id_chunks) >= 10:  # show progress bar for batches which may take a long time
            bar = self.get_progress_bar(iterable=bar, desc=f"Getting {unit}", unit="pages")

        results: list[dict[str, Any]] = []
        params = params if params is not None else {}
        for idx in bar:  # get responses in batches
            id_chunk = id_chunks[idx]
            params_chunk = params | {"ids": ",".join(id_chunk)}
            log = [f"{unit.title() + ':':<11} {len(results) + len(id_chunk):>6}/{len(id_list):<6}"]

            response = self.get(url, params=params_chunk, use_cache=use_cache, log_pad=43, log_extra=log)
            if key and key not in response:
                raise APIError(f"Given key '{key}' not found in response keys: {list(response.keys())}")

            results.extend(response[key]) if key else results.append(response)

        return results

    def extend_items(
            self, items_block: MutableMapping[str, Any], key: str, unit: str, use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Extend the items for a given ``items_block`` API response.
        The function requests each page of the collection returning a list of all items
        found across all pages for this URL.

        Updates the value of the ``items`` key in-place by extending the value of the ``items`` key with new results.

        :param items_block: A remote API JSON response for an items type endpoint which includes a required
            ``next`` key plus optional keys ``total``, ``limit``, ``items`` etc.
        :param key: The child unit to use when selecting nested data for certain responses e.g. user's followed artists
            and for logging.
        :param unit: The parent unit to use for logging.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item
        """
        if key.rstrip("s") + "s" in items_block:
            items_block = items_block[key.rstrip("s") + "s"]
        if self.items_key not in items_block:
            items_block[self.items_key] = []

        # enable progress bar for longer calls
        total = items_block["total"]
        initial = len(items_block[self.items_key])
        bar = self.get_progress_bar(total=total, desc=f"Getting {unit}", unit=key, initial=initial)

        # this usually happens on the items block of a current user's playlist
        if "limit" not in items_block:
            items_block["limit"] = 50
        if "next" not in items_block:
            items_block["next"] = items_block["href"]

        if "cursors" in items_block:  # happens on some item types e.g. user's followed artists
            items_block["next"] = items_block["cursors"].get("after")
            items_block["previous"] = items_block["cursors"].get("before")

        response = items_block
        while response.get("next"):  # loop through each page
            log_count = min(bar.n + response["limit"], response["total"])
            log = [f"{log_count:>6}/{response["total"]:<6} {unit}"]

            response = self.get(response["next"], use_cache=use_cache, log_pad=95, log_extra=log)
            if key.rstrip("s") + "s" in response:
                response = response[key.rstrip("s") + "s"]
            items_block[self.items_key].extend(response[self.items_key])

            sleep(0.1)
            bar.update(len(response[self.items_key]))

            if "cursors" in response:  # happens on some item types e.g. user's followed artists
                response["next"] = response["cursors"].get("after")
                response["previous"] = response["cursors"].get("before")

        if bar is not None:
            bar.close()

        return items_block[self.items_key]

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_items(
            self,
            values: APIMethodInputType,
            kind: RemoteObjectType | None = None,
            limit: int = 50,
            extend: bool = True,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` - Get information for given list of ``values``. Items may be:
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

        :param values: The values representing some remote objects. See description for allowed value types.
            These items must all be of the same type of item i.e. all tracks OR all artists etc.
        :param kind: Item type if given string is ID.
        :param limit: When requests can be batched, size of batches to request.
        :param extend: When True and the given ``kind`` is a collection of items,
            extend the response to include all items in this collection.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item.
        :raise RemoteObjectTypeError: Raised when the function cannot determine the item type
            of the input ``values``. Or when it does not recognise the type of the input ``values`` parameter.
        """
        # input validation
        if kind is None:  # determine the item type
            kind = self.get_item_type(values)
        else:
            self.validate_item_type(values, kind=kind)

        unit = kind.name.casefold() + "s"
        url = f"{self.api_url_base}/{unit}"
        id_list = self.extract_ids(values, kind=kind)

        if kind in {RemoteObjectType.USER, RemoteObjectType.PLAYLIST} or len(id_list) <= 1:
            results = self._get_items_multi(url=url, id_list=id_list, unit=unit, use_cache=use_cache)
        else:
            results = self._get_items_batched(url=url, id_list=id_list, key=unit, use_cache=use_cache, limit=limit)

        if len(results) == 0 or kind not in self.collection_item_map or not extend:
            self.logger.debug(f"{'DONE':<7}: {url:<43} | Retrieved {len(results):>6} {unit}")
            self._merge_results_to_input(original=values, results=results, ordered=True)
            return results

        bar = results
        key = self.collection_item_map.get(kind, kind).name.casefold() + "s"
        if len(id_list) > 5:  # show progress bar for collection batches which may take a long time
            bar = self.get_progress_bar(iterable=results, desc=f"Extending {unit}", unit=key)

        for result in bar:
            if result[key]["next"]:
                self.extend_items(result[key], key=key, unit=unit, use_cache=use_cache)

        item_count = sum(len(result[key][self.items_key]) for result in results)
        self.logger.debug(
            f"{'DONE':<7}: {url:<71} | Retrieved {item_count:>6} {key} across {len(results):>5} {unit}"
        )
        self._merge_results_to_input(original=values, results=results, ordered=True)

        return results

    def get_user_items(
            self,
            user: str | None = None,
            kind: RemoteObjectType = RemoteObjectType.PLAYLIST,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` - Get saved items for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type to retrieve for the user.
            Spotify only supports ``PLAYLIST`` types for non-authenticated users.
        :param limit: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and ``50``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each collection.
        :raise RemoteIDTypeError: Raised when the input ``user`` does not represent a user URL/URI/ID.
        :raise RemoteObjectTypeError: Raised a user is given and the ``kind`` is not ``PLAYLIST``.
            Or when the given ``kind`` is not a valid collection.
        """
        # input validation
        if kind not in self.user_item_types:
            raise RemoteObjectTypeError(f"{kind.name.title()}s are not a valid user collection type", kind=kind)
        if kind != RemoteObjectType.PLAYLIST and user is not None:
            raise RemoteObjectTypeError(
                f"Only able to retrieve {kind.name.casefold()}s from the currently authenticated user",
                kind=kind
            )

        unit = kind.name.casefold() + "s"
        params = {"limit": limit_value(limit, floor=1, ceil=50)}

        if user is not None:
            url = f"{self.convert(user, kind=RemoteObjectType.USER, type_out=RemoteIDType.URL)}/{kind.name.casefold()}s"
            unit_prefix = "user"
        elif kind == RemoteObjectType.ARTIST:
            url = f"{self.api_url_base}/me/following"
            unit_prefix = "current user's followed"
            params["type"] = "artist"
        else:
            url = f"{self.api_url_base}/me/{kind.name.casefold()}s"
            unit_prefix = "current user's" if kind == RemoteObjectType.PLAYLIST else "current user's saved"

        initial = self.get(url, params=params, use_cache=use_cache, log_pad=71)
        results = self.extend_items(initial, key=unit, unit=f"{unit_prefix} {unit}", use_cache=use_cache)

        self.logger.debug(f"{'DONE':<7}: {url:<43} | Retrieved {len(results):>6} {unit}")

        return results

    def get_tracks_extra(
            self,
            values: APIMethodInputType,
            features: bool = False,
            analysis: bool = False,
            limit: int = 50,
            use_cache: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        ``GET: /audio-features`` and/or ``GET: /audio-analysis`` - Get audio features/analysis for list of items.
        Items may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a collection including:
                - some items under an ``items`` key
                - a valid ID value under an ``id`` key.

        If a JSON response is given, this updates ``items`` by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        :param values: The values representing some remote tracks. See description for allowed value types.
        :param features: When True, get audio features.
        :param analysis: When True, get audio analysis.
        :param limit: Size of batches to request when getting audio features.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``values``
            are not all tracks or IDs.
        """
        # input validation
        if not features and not analysis:  # skip on all False
            return {}
        if not values:  # skip on empty
            self.logger.debug(f"{'SKIP':<7}: {self.api_url_base:<43} | No data given")
            return {}
        self.validate_item_type(values, kind=RemoteObjectType.TRACK)

        id_list = self.extract_ids(values, kind=RemoteObjectType.TRACK)

        # value list takes the form [url, key, batched]
        config: dict[str, tuple[str, str, bool]] = {}
        if features:
            config["features"] = (f"{self.api_url_base}/audio-features", "audio_features", True)
        if analysis:
            config["analysis"] = (f"{self.api_url_base}/audio-analysis", "audio_analysis", False)

        results: dict[str, list[dict[str, Any]]] = {}
        if len(id_list) == 1:
            for (url, key, _) in config.values():
                results[key] = [self.get(f"{url}/{id_list[0]}", use_cache=use_cache, log_pad=43)]
        else:
            for unit, (url, key, batch) in config.items():
                method = self._get_items_batched if batch else self._get_items_multi
                results[key] = method(
                    url=url, id_list=id_list, key=key if batch else None, unit=unit, limit=limit, use_cache=use_cache
                )

        self._extend_input_with_results(original=values, results=results, ordered=True)

        return results

    def get_tracks(
            self,
            values: APIMethodInputType,
            features: bool = False,
            analysis: bool = False,
            limit: int = 50,
            use_cache: bool = True,
            *_,
            **__,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` + GET: /audio-features`` and/or ``GET: /audio-analysis``

        Get audio features/analysis for list of tracks.
        Mostly just a wrapper for ``get_items`` and ``get_tracks`` functions.
        Values may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a collection including :
                - some items under an ``items`` key
                - a valid ID value under an ``id`` key.

        If a JSON response is given, this updates ``items`` by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        :param values: The values representing some remote tracks. See description for allowed value types.
        :param features: When True, get audio features.
        :param analysis: When True, get audio analysis.
        :param limit: Size of batches to request when getting audio features.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item, or the original response if the input ``values`` are API responses.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``tracks``
            are not all tracks or IDs.
        """
        tracks = self.get_items(values=values, kind=RemoteObjectType.TRACK, limit=limit, use_cache=use_cache)

        # ensure that response are being assigned back to the original values if API response/s given
        if isinstance(values, Mapping):
            tracks = [values]
        elif isinstance(values, Collection) and all(isinstance(v, Mapping) for v in values):
            tracks = values

        self.get_tracks_extra(values=tracks, features=features, analysis=analysis, limit=limit, use_cache=use_cache)
        return tracks
