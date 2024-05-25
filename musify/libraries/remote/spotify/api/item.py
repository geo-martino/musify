"""
Implements endpoints for getting items from the Spotify API.
"""
import re
from abc import ABC
from collections.abc import Collection, Mapping, MutableMapping
from copy import copy
from itertools import batched
from typing import Any

from yarl import URL

from musify.api.cache.session import CachedSession
from musify.api.exception import APIError, CacheError
from musify.libraries.remote.core import RemoteResponse
from musify.libraries.remote.core.enum import RemoteIDType, RemoteObjectType
from musify.libraries.remote.core.exception import RemoteObjectTypeError
from musify.libraries.remote.core.types import APIInputValue
from musify.libraries.remote.spotify.api.base import SpotifyAPIBase
from musify.utils import limit_value, to_collection

try:
    import tqdm
except ImportError:
    tqdm = None

ARTIST_ALBUM_TYPES = {"album", "single", "compilation", "appears_on"}


class SpotifyAPIItems(SpotifyAPIBase, ABC):

    __slots__ = ()

    _bar_threshold = 5

    def _get_unit(self, key: str | None = None, kind: str | None = None) -> str:
        """Determine the unit type to use in the progress bar"""
        if kind is None:
            kind = re.sub(r"[-_]+", " ", key) if key is not None else self.items_key
        return kind.casefold().rstrip("s") + "s"

    ###########################################################################
    ## GET helpers: Generic methods for getting items
    ###########################################################################
    async def _cache_results(self, method: str, results: list[dict[str, Any]]) -> None:
        """Persist ``results`` of a given ``method`` to the cache."""
        if not isinstance(self.handler.session, CachedSession) or not results:
            return

        def _get_href_from_result(r: dict[str, Any]) -> str:
            if "track_href" in r:
                return r["track_href"]
            return r.get(self.url_key, "")

        # take all parts of href path, excluding ID
        possible_urls = {"/".join(_get_href_from_result(result).split("/")[:-1]) for result in results}
        possible_urls = {url for url in possible_urls if url}
        if not possible_urls:
            return
        if len(possible_urls) > 1:
            raise CacheError(
                "Too many different types of results given. Given results must relate to the same repository type."
            )

        results_mapped = {(method.upper(), result[self.id_key]): result for result in results}
        repository = self.handler.session.cache.get_repository_from_url(next(iter(possible_urls)))
        if repository is not None:
            await repository.save_responses(results_mapped)

    def _sort_results(
            self, results: list[dict[str, Any]], results_cache: list[dict[str, Any]], id_list: Collection[str]
    ) -> None:
        """Extend ``results`` with ``results_cache`` and sort by order of ``id_list``."""
        if not results_cache:  # cache was not used
            return

        results += results_cache
        id_list = to_collection(id_list)
        results.sort(key=lambda result: id_list.index(result[self.id_key]))

    async def _get_items_from_cache(
            self, method: str, url: str | URL, id_list: Collection[str]
    ) -> tuple[list[dict[str, Any]], Collection[str], Collection[str]]:
        """
        Attempt to find the given ``id_list`` in the cache of the request handler and return results.

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :return: (Results from the cache, IDs found in the cache, IDs not found in the cache)
        """
        if not isinstance(self.handler.session, CachedSession):
            self.handler.log("CACHE", url, message="Cache not configured, skipping...")
            return [], [], id_list

        repository = self.handler.session.cache.get_repository_from_url(url=url)
        if repository is None:
            self.handler.log("CACHE", url, message="No repository for this endpoint, skipping...")
            return [], [], id_list

        results = await repository.get_responses([(method.upper(), id_,) for id_ in id_list])
        ids_found = {result[self.id_key] for result in results}
        ids_not_found = {id_ for id_ in id_list if id_ not in ids_found}

        self.handler.log(
            method="CACHE",
            url=url,
            message=[f"Retrieved {len(results):>6} cached responses", f"{len(ids_not_found):>6} not found in cache"]
        )
        return results, ids_found, ids_not_found

    async def _get_items_multi(
            self,
            url: str | URL,
            id_list: Collection[str],
            params: Mapping[str, Any] | None = None,
            key: str | None = None,
            kind: str | None = None,
            *_,
            **__,
    ) -> list[dict[str, Any]]:
        """
        Get responses from a given ``url`` appending an ID to each request from a given ``id_list``
        i.e. ``URL`` or ``ID``.
        This function executes each URL request individually for each ID i.e. ``URL`` or ``ID``.

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param kind: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param key: The key to reference from each response to get the list of required values.
        :return: API JSON responses for each item at the given ``key``.
        :raise APIError: When the given ``key`` is not in the API response.
        """
        method = "GET"
        url = url.rstrip("/")
        kind = self._get_unit(key=key, kind=kind)

        results_cache, ids_cached, ids_not_cached = await self._get_items_from_cache(
            method=method, url=url, id_list=id_list
        )

        bar = self.logger.get_iterator(
            iterable=ids_not_cached,
            desc=f"Getting {kind}",
            unit=kind,
            disable=len(ids_not_cached) < self._bar_threshold
        )

        results: list[dict[str, Any]] = []
        log = f"{kind.title()}: {len(ids_not_cached):>5}"
        for id_ in bar:
            href = f"{url}/{id_}"
            response = await self.handler.request(
                method=method, url=href, params=params, persist=False, log_message=log
            )
            if self.id_key not in response:
                response[self.id_key] = id_
            if self.url_key not in response:
                response[self.url_key] = href

            if key and key not in response:
                raise APIError(f"Given key '{key}' not found in response keys: {list(response.keys())}")
            results.extend(response[key]) if key else results.append(response)

        await self._cache_results(method=method, results=results)
        self._sort_results(results=results, results_cache=results_cache, id_list=id_list)

        return results

    async def _get_items_batched(
            self,
            url: str | URL,
            id_list: Collection[str],
            params: Mapping[str, Any] | None = None,
            key: str | None = None,
            kind: str | None = None,
            limit: int = 50,
            *_,
            **__,
    ) -> list[dict[str, Any]]:
        """
        Get responses from a given ``url`` appending an ID to each request from a given ``id_list``
        i.e. ``URL`` or ``ID``.
        This function executes each URL request in batches of IDs based on the given ``batch_size``.
        It passes this chunked list of IDs to the request handler as a set of params in the form:
        ``{<IDs>: '<comma separated string of IDs>'}``

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param kind: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param key: The key to reference from each response to get the list of required values.
        :param limit: Size of each batch of IDs to get. This value will be limited to be between ``1`` and ``50``.
        :return: API JSON responses for each item at the given ``key``.
        :raise APIError: When the given ``key`` is not in the API response.
        """
        method = "GET"
        url = url.rstrip("/")
        kind = self._get_unit(key=key, kind=kind)

        results_cache, ids_cached, ids_not_cached = await self._get_items_from_cache(
            method=method, url=url, id_list=id_list
        )

        id_chunks = list(batched(ids_not_cached, limit_value(limit, floor=1, ceil=50)))
        bar = self.logger.get_iterator(
            iterable=range(len(id_chunks)),
            desc=f"Getting {kind}",
            unit="pages",
            disable=len(id_chunks) < self._bar_threshold
        )

        results: list[dict[str, Any]] = []
        params = params if params is not None else {}
        for idx in bar:  # get responses in batches
            id_chunk = id_chunks[idx]
            params_chunk = params | {"ids": ",".join(id_chunk)}
            log = f"{kind.title() + ':':<11} {len(results) + len(id_chunk):>6}/{len(ids_not_cached):<6}"

            response = await self.handler.request(
                method=method, url=url, params=params_chunk, persist=False, log_message=log
            )
            if key and key not in response:
                raise APIError(f"Given key '{key}' not found in response keys: {list(response.keys())}")

            results.extend(response[key]) if key else results.append(response)

        await self._cache_results(method=method, results=results)
        self._sort_results(results=results, results_cache=results_cache, id_list=id_list)

        return results

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def _reformat_user_items_block(self, response: MutableMapping[str, Any]) -> None:
        """this usually happens on the items block of a current user's playlist"""
        if "next" not in response:
            response["next"] = response[self.url_key]
        if "previous" not in response:
            response["previous"] = None
        if "limit" not in response:
            response["limit"] = int(URL(response["next"]).query.get("limit", 50))

    def _enrich_with_parent_response(
            self,
            response: MutableMapping[str, Any],
            key: str,
            parent_key: RemoteObjectType | None,
            parent_response: MutableMapping[str, Any]
    ) -> None:
        """
        Some endpoints don't include parent response on child items.
        This method adds the given ``parent_response`` back to the child ``response`` on the given ``key``.
        """
        if (
                not parent_key
                or isinstance(parent_key, str)
                or parent_key == RemoteObjectType.PLAYLIST
                or self.items_key in parent_response
        ):
            return

        parent_key_name = self._get_key(parent_key).rstrip("s")
        parent_response = {k: v for k, v in parent_response.items() if k != key}

        if not parent_response:
            return

        for item in response[self.items_key]:
            if parent_key_name not in item:
                item[parent_key_name] = parent_response

    async def extend_items(
            self,
            response: MutableMapping[str, Any] | RemoteResponse,
            kind: RemoteObjectType | str | None = None,
            key: RemoteObjectType | None = None,
            leave_bar: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extend the items for a given API ``response``.
        The function requests each page of the collection returning a list of all items
        found across all pages for this URL.

        Updates the value of the ``items`` key in-place by extending the value of the ``items`` key with new results.

        If a cache has been configured for this API, will also persist the items in any collection to the cache.

        If a :py:class:`RemoteResponse`, this function will not refresh itself with the new response.
        The user must call `refresh` manually after execution.

        :param response: A remote API JSON response for an items type endpoint
            or a response/RemoteResponse which contains this response.
            Must include required keys:
            ``total`` and either ``next`` or ``href``, plus optional keys ``previous``, ``limit``, ``items`` etc.
        :param kind: The type of response being extended.
            If a RemoteObjectType is given, the method will attempt to enrich the items given
            and returned with given response on the key associated with this kind. The function will only do this
            if a parent response has been given and not an items block response.
        :param key: The type of response of the child objects. Used when selecting nested data for certain responses
            (e.g. user's followed artists).
        :param leave_bar: When a progress bar is displayed,
            toggle whether this bar should continue to be displayed after the operation is finished.
            When None, allow the logger to decide this setting.
        :return: API JSON responses for each item
        """
        if isinstance(response, RemoteResponse):
            response = response.response

        method = "GET"

        parent_key = kind
        parent_response = copy(response)

        key = self._get_key(key)
        response = response.get(key, response)
        if self.items_key not in response:
            response[self.items_key] = []

        self._enrich_with_parent_response(
            response=response, key=key, parent_key=parent_key, parent_response=parent_response
        )

        if len(response[self.items_key]) == response["total"]:  # skip on fully extended response
            url = URL(response[self.url_key]).with_query(None)
            self.handler.log("SKIP", url, message="Response already extended")
            return response[self.items_key]

        self._reformat_user_items_block(response)

        kind_name = self._get_key(kind) or self.items_key
        pages = (response["total"] - len(response[self.items_key])) / (response["limit"] or 1)
        bar = self.logger.get_iterator(
            initial=len(response[self.items_key]),
            total=response["total"],
            desc=f"Extending {kind_name}".rstrip("s") if kind_name[0].islower() else kind_name,
            unit=key or self.items_key,
            leave=leave_bar,
            disable=pages < self._bar_threshold,
        )

        while response.get("next"):  # loop through each page
            log_count = min(len(response[self.items_key]) + response["limit"], response["total"])
            log = f"{log_count:>6}/{response["total"]:<6} {key or self.items_key}"

            response_next = await self.handler.request(method=method, url=response["next"], log_message=log)
            response_next = response_next.get(key, response_next)
            if self.items_key not in response_next:
                self.logger.print_message(response)
            self._enrich_with_parent_response(
                response=response_next, key=key, parent_key=parent_key, parent_response=parent_response
            )

            response[self.items_key].extend(response_next[self.items_key])
            response[self.url_key] = response_next[self.url_key]
            response["next"] = response_next.get("next")
            response["previous"] = response_next.get("previous")

            if tqdm is not None:  # TODO: drop me when optimising
                bar.update(len(response_next[self.items_key]))

        # cache child items
        key = key.rstrip("s") if key else key
        results_to_cache = [
            result[key] if key and key in result else result for result in response[self.items_key]
        ]
        await self._cache_results(method=method, results=results_to_cache)

        if tqdm is not None:  # TODO: drop me when optimising
            bar.close()

        return response[self.items_key]

    async def get_items(
            self,
            values: APIInputValue,
            kind: RemoteObjectType | None = None,
            limit: int = 50,
            extend: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` - Get information for given ``values``.

        ``values`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including:
                - some items under an ``items`` key,
                - a valid ID value under an ``id`` key,
                - a valid item type value under a ``type`` key if ``kind`` is None.
            * A MutableSequence of remote API JSON responses for a collection including the same structure as above.
            * A RemoteResponse of the appropriate type for this RemoteAPI which holds a valid API JSON response
              as described above.
            * A Sequence of RemoteResponses as above.

        If JSON response(s) given, this update each response given by merging with the new response
        and replacing the ``items`` with the new results.

        If :py:class:`RemoteResponse` values are given, this function will call `refresh` on them.

        :param values: The values representing some remote objects. See description for allowed value types.
            These items must all be of the same type of item i.e. all tracks OR all artists etc.
        :param kind: Item type if given string is ID.
        :param limit: When requests can be batched, size of batches to request.
            This value will be limited to be between ``1`` and ``50`` or ``20`` if getting albums.
        :param extend: When True and the given ``kind`` is a collection of items,
            extend the response to include all items in this collection.
        :return: API JSON responses for each item.
        :raise RemoteObjectTypeError: Raised when the function cannot determine the item type
            of the input ``values``. Or when it does not recognise the type of the input ``values`` parameter.
        """
        # input validation
        if not isinstance(values, RemoteResponse) and not values:  # skip on empty
            url = f"{self.url}/{self._get_key(kind)}" if kind else self.url
            self.handler.log("SKIP", url, message="No data given")
            return []
        if kind is None:  # determine the item type
            kind = self.wrangler.get_item_type(values)
        else:
            self.wrangler.validate_item_type(values, kind=kind)

        unit = self._get_key(kind)
        url = f"{self.url}/{unit}"
        id_list = self.wrangler.extract_ids(values, kind=kind)

        if kind in {RemoteObjectType.USER, RemoteObjectType.PLAYLIST} or len(id_list) <= 1:
            results = await self._get_items_multi(url=url, id_list=id_list, kind=unit)
        else:
            if kind == RemoteObjectType.ALBUM:
                limit = limit_value(limit, floor=1, ceil=20)
            results = await self._get_items_batched(url=url, id_list=id_list, key=unit, limit=limit)

        key = self.collection_item_map.get(kind, kind)
        key_name = self._get_key(key)
        if len(results) == 0 or any(key_name not in result for result in results) or not extend:
            self._merge_results_to_input(original=values, responses=results, ordered=True)
            self._refresh_responses(responses=values, skip_checks=False)
            self.handler.log("DONE", url, message=f"Retrieved {len(results):>6} {unit}")
            return results

        bar = self.logger.get_iterator(
            iterable=results, desc=f"Extending {unit}", unit=unit, disable=len(id_list) < self._bar_threshold
        )

        for result in bar:
            if result[key_name].get("next") or ("next" not in result[key_name] and result[key_name].get(self.url_key)):
                self.handler.log("INFO", url, message=f"Extending {key_name} on {unit}")
                await self.extend_items(result, kind=kind, key=key, leave_bar=False)

        self._merge_results_to_input(original=values, responses=results, ordered=True)
        self._refresh_responses(responses=values, skip_checks=False)

        item_count = sum(len(result[key_name][self.items_key]) for result in results)
        self.handler.log("DONE", url, message=f"Retrieved {item_count:>6} {key_name} across {len(results):>5} {unit}")

        return results

    async def get_user_items(
            self,
            user: str | None = None,
            kind: RemoteObjectType = RemoteObjectType.PLAYLIST,
            limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` - Get saved items for a given user.

        :param user: The ID of the user to get playlists for. If None, use the currently authenticated user.
        :param kind: Item type to retrieve for the user.
            Spotify only supports ``PLAYLIST`` types for non-authenticated users.
        :param limit: Size of each batch of items to request in the collection items request.
            This value will be limited to be between ``1`` and ``50``.
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
                f"Only able to retrieve {kind.name.lower()}s from the currently authenticated user",
                kind=kind
            )

        params = {"limit": limit_value(limit, floor=1, ceil=50)}
        if user is not None:
            url = self.wrangler.convert(user, kind=RemoteObjectType.USER, type_out=RemoteIDType.URL)
            url = f"{url}/{kind.name.lower()}s"
            desc_qualifier = "user's"
        elif kind == RemoteObjectType.ARTIST:
            url = f"{self.url}/me/following"
            desc_qualifier = "current user's followed"
            params["type"] = "artist"
        else:
            url = f"{self.url}/me/{kind.name.lower()}s"
            desc_qualifier = "current user's" if kind == RemoteObjectType.PLAYLIST else "current user's saved"

        desc = f"Getting {desc_qualifier} {kind.name.lower()}s"
        initial = await self.handler.get(url, params=params)
        results = await self.extend_items(initial, kind=desc, key=kind)

        self.handler.log("DONE", url, message=f"Retrieved {len(results):>6} {kind.name.lower()}s")

        return results

    async def extend_tracks(
            self,
            values: APIInputValue,
            features: bool = False,
            analysis: bool = False,
            limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /audio-features`` and/or ``GET: /audio-analysis`` - Get audio features/analysis for given track/s.

        ``values`` may be:
            * A string representing a URL/URI/ID of type 'track'.
            * A MutableSequence of strings representing URLs/URIs/IDs of the type 'track'.
            * A remote API JSON response for a track including:
                - some items under an ``items`` key,
                - a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a set of tracks including the same structure as above.
            * A RemoteResponse of the appropriate type for this RemoteAPI which holds a valid API JSON response
              as described above.
            * A Sequence of RemoteResponses as above.

        If JSON response(s) given, this updates each response given by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        If :py:class:`RemoteResponse` values are given, this function will call `refresh` on them.

        :param values: The values representing some remote track/s. See description for allowed value types.
        :param features: When True, get audio features.
        :param analysis: When True, get audio analysis.
        :param limit: Size of batches to request when getting audio features.
            This value will be limited to be between ``1`` and ``50``.
        :return: API JSON responses for each item.
            Mapped to ``audio_features`` and ``audio_analysis`` keys as appropriate.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``values`` are not all tracks or IDs.
        """
        # input validation
        if not features and not analysis:  # skip on all False
            return []
        if not values:  # skip on empty
            self.handler.log("SKIP", self.url, message="No data given")
            return []
        self.wrangler.validate_item_type(values, kind=RemoteObjectType.TRACK)

        id_list = self.wrangler.extract_ids(values, kind=RemoteObjectType.TRACK)

        # value list takes the form [URL, key, batched]
        config: dict[str, tuple[str, str, bool]] = {}
        if features:
            config["features"] = (f"{self.url}/audio-features", "audio_features", True)
        if analysis:
            config["analysis"] = (f"{self.url}/audio-analysis", "audio_analysis", False)

        results: list[dict[str, Any]]
        if len(id_list) == 1:
            id_ = id_list[0]
            id_map = {self.id_key: id_}

            result = id_map.copy()
            for (url, key, _) in config.values():
                result[key] = await self.handler.get(f"{url}/{id_}") | id_map.copy()
            results = [result]
        else:
            results = []
            for kind, (url, key, batch) in config.items():
                method = self._get_items_batched if batch else self._get_items_multi
                responses = await method(url=url, id_list=id_list, kind=kind, key=key if batch else None, limit=limit)
                responses.sort(key=lambda response: id_list.index(response[self.id_key]))
                responses = [{self.id_key: response[self.id_key], key: response} for response in responses]

                if not results:
                    results = responses
                else:
                    results = [result | response for result, response in zip(results, responses)]

        self._merge_results_to_input(original=values, responses=results, ordered=False, clear=False)
        self._refresh_responses(responses=values, skip_checks=False)

        def map_key(value: str) -> str:
            """Map the given ``value`` to logging appropriate string"""
            return value.replace("_", " ").replace("analysis", "analyses")

        log_types = " and ".join(map_key(key) for _, key, _ in config.values())
        self.handler.log(
            method="DONE",
            url=f"{self.url}/{"+".join(c[0].split("/")[-1] for c in config.values())}",
            message=f"Retrieved {log_types} for {len(id_list):>5} tracks"
        )

        return results

    async def get_tracks(
            self,
            values: APIInputValue,
            features: bool = False,
            analysis: bool = False,
            limit: int = 50,
            *_,
            **__,
    ) -> list[dict[str, Any]]:
        """
        ``GET: /{kind}s`` + ``GET: /audio-features`` and/or ``GET: /audio-analysis``

        Get track(s) info and any audio features/analysis.
        Mostly just a wrapper for ``get_items`` and ``extend_tracks`` functions.

        ``values`` may be:
            * A string representing a URL/URI/ID of type 'track'.
            * A MutableSequence of strings representing URLs/URIs/IDs of the type 'track'.
            * A remote API JSON response for a track including:
                - some items under an ``items`` key,
                - a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a set of tracks including the same structure as above.
            * A RemoteResponse of the appropriate type for this RemoteAPI which holds a valid API JSON response
              as described above.
            * A Sequence of RemoteResponses as above.

        If JSON response(s) given, this updates each response given by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        :param values: The values representing some remote track/s. See description for allowed value types.
        :param features: When True, get audio features.
        :param analysis: When True, get audio analysis.
        :param limit: Size of batches to request when getting audio features.
            This value will be limited to be between ``1`` and ``50``.
        :return: API JSON responses for each item, or the original response if the input ``values`` are API responses.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``values`` are not all tracks or IDs.
        """
        tracks = await self.get_items(values=values, kind=RemoteObjectType.TRACK, limit=limit)

        # ensure that response are being assigned back to the original values if API response(s) given
        if isinstance(values, Mapping | RemoteResponse):
            tracks = [values]
        elif isinstance(values, Collection) and all(isinstance(v, Mapping | RemoteResponse) for v in values):
            tracks = values

        await self.extend_tracks(values=tracks, features=features, analysis=analysis, limit=limit)
        return tracks

    async def get_artist_albums(
            self, values: APIInputValue, types: Collection[str] = (), limit: int = 50,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        ``GET: /artists/{ID}/albums`` - Get all albums associated with the given artist/s.

        ``values`` may be:
            * A string representing a URL/URI/ID of type 'artist'.
            * A MutableSequence of strings representing URLs/URIs/IDs of the type 'artist'.
            * A remote API JSON response for an artist including a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a set of artists including the same structure as above.
            * A RemoteResponse of the appropriate type for this RemoteAPI which holds a valid API JSON response
              as described above.
            * A Sequence of RemoteResponses as above.

        If JSON response(s) given, this updates each response given by adding the results under the ``albums`` key.

        If :py:class:`RemoteResponse` values are given, this function will call `refresh` on them.

        :param values: The values representing some remote artist/s. See description for allowed value types.
        :param types: The types of albums to return. Select from ``{"album", "single", "compilation", "appears_on"}``.
        :param limit: Size of batches to request.
            This value will be limited to be between ``1`` and ``50``.
        :return: A map of the Artist ID to a list of the API JSON responses for each album.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``values`` are not all artists or IDs.
        """
        url = f"{self.url}/artists/{{id}}/albums"

        # input validation
        if not isinstance(values, RemoteResponse) and not values:  # skip on empty
            self.handler.log("SKIP", url, message="No data given")
            return {}

        if types and not all(t in ARTIST_ALBUM_TYPES for t in types):
            raise APIError(
                f"Given types not recognised, must be one or many of the following: {ARTIST_ALBUM_TYPES} ({types})"
            )
        self.wrangler.validate_item_type(values, kind=RemoteObjectType.ARTIST)

        id_list = self.wrangler.extract_ids(values, kind=RemoteObjectType.ARTIST)
        bar = self.logger.get_iterator(
            iterable=id_list, desc="Getting artist albums", unit="artist", disable=len(id_list) < self._bar_threshold
        )

        params = {"limit": limit_value(limit, floor=1, ceil=50)}
        if types:
            params["include_groups"] = ",".join(set(types))

        key = RemoteObjectType.ALBUM
        results: dict[str, dict[str, Any]] = {}
        for id_ in bar:
            results[id_] = await self.handler.get(url=url.format(id=id_), params=params)
            await self.extend_items(results[id_], kind="artist albums", key=key, leave_bar=False)

            for album in results[id_][self.items_key]:  # add skeleton items block to album responses
                album["tracks"] = {
                    self.url_key: self.format_next_url(
                        url=str(URL(album[self.url_key]).with_query(None)) + "/tracks", offset=0, limit=50
                    ),
                    "total": album["total_tracks"]
                }

        results_remapped = [{self.id_key: id_, "albums": result} for id_, result in results.items()]
        self._merge_results_to_input(original=values, responses=results_remapped, ordered=False, clear=False)
        self._refresh_responses(responses=values, skip_checks=True)

        item_count = sum(len(result) for result in results.values())
        self.handler.log(
            method="DONE",
            url=url.format(id="..."),
            message=f"Retrieved {item_count:>6} albums across {len(results):>5} artists",
        )

        return {k: v[self.items_key] for k, v in results.items()}
