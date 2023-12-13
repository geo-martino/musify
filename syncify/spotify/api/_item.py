import re
from abc import ABCMeta
from collections.abc import Sequence
from itertools import batched
from typing import Any, Collection, Mapping

from syncify.api.exception import APIError
from syncify.remote.api import RemoteAPI, APIMethodInputType
from syncify.remote.enums import RemoteItemType
from syncify.utils.helpers import limit_value


class SpotifyAPIItems(RemoteAPI, metaclass=ABCMeta):

    @staticmethod
    def _get_unit(key: str | None = None, unit: str | None = None) -> str:
        """Determine the unit type to use in the progress bar"""
        if unit is None:
            unit = re.sub(r"[-_]+", " ", key) if key is not None else "items"
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
            params_chunk = params | {"ids": ','.join(id_chunk)}
            log = [f"{unit.title() + ':':<11} {len(results) + len(id_chunk):>6}/{len(id_list):<6}"]

            response = self.get(url, params=params_chunk, use_cache=use_cache, log_pad=43, log_extra=log)
            if key and key not in response:
                raise APIError(f"Given key '{key}' not found in response keys: {list(response.keys())}")

            results.extend(response[key]) if key else results.append(response)

        return results

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_items(
            self,
            values: APIMethodInputType,
            kind: RemoteItemType | None = None,
            limit: int = 50,
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

        :param values: The values representing some remote items. See description for allowed value types.
            These items must all be of the same type of item i.e. all tracks OR all artists etc.
        :param kind: Item type if given string is ID.
        :param limit: When requests can be batched, size of batches to request.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item.
        :raise RemoteItemTypeError: Raised when the function cannot determine the item type
            of the input ``values``. Or when it does not recognise the type of the input ``values`` parameter.
        """
        # input validation
        if kind is None:  # determine the item type
            kind = self.get_item_type(values)
        else:
            self.validate_item_type(values, kind=kind)

        kind_str = kind.name.casefold() + "s"
        url = f"{self.api_url_base}/{kind_str}"
        id_list = self.extract_ids(values, kind=kind)

        if kind == RemoteItemType.USER or kind == RemoteItemType.PLAYLIST or len(id_list) <= 1:
            results = self._get_items_multi(url=url, id_list=id_list, unit=kind_str, use_cache=use_cache)
        else:
            results = self._get_items_batched(url=url, id_list=id_list, key=kind_str, use_cache=use_cache, limit=limit)

        self.logger.debug(f"{'DONE':<7}: {url:<43} | Retrieved {len(results):>6} {kind_str}")
        self._merge_results_to_input(original=values, results=results, ordered=True)

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
        :raise RemoteItemTypeError: Raised when the item types of the input ``values``
            are not all tracks or IDs.
        """
        # input validation
        if not features and not analysis:  # skip on all False
            return {}
        if not values:  # skip on empty
            self.logger.debug(f"{'SKIP':<7}: {self.api_url_base:<43} | No data given")
            return {}
        self.validate_item_type(values, kind=RemoteItemType.TRACK)

        id_list = self.extract_ids(values, kind=RemoteItemType.TRACK)

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
    ) -> list[dict[str, Any]] | dict[str, Any]:
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
        :raise RemoteItemTypeError: Raised when the item types of the input ``tracks``
            are not all tracks or IDs.
        """
        tracks = self.get_items(values=values, kind=RemoteItemType.TRACK, limit=limit, use_cache=use_cache)

        # ensure that response are being assigned back to the original values if API response/s given
        is_response_sequence = (isinstance(values, Sequence) and all(isinstance(v, Mapping) for v in values))
        if isinstance(values, Mapping) or is_response_sequence:
            tracks = values

        self.get_tracks_extra(values=tracks, features=features, analysis=analysis, limit=limit, use_cache=use_cache)
        return tracks
