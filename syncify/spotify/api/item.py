import re
from abc import ABCMeta
from typing import Optional, List, MutableMapping, Mapping, Any
from syncify.spotify import __URL_API__, ItemType, APIMethodInputType
from syncify.spotify.utils import validate_item_type, get_item_type, extract_ids
from syncify.spotify.api.basic import APIBase
from syncify.utils import chunk, limit_value


class Items(APIBase, metaclass=ABCMeta):
    """Spotify API endpoints for processing all Spotify item types"""

    ###########################################################################
    ## GET helpers: Generic methods for getting items
    ###########################################################################
    def _get_item_results(
            self,
            url: str,
            id_list: List[str],
            params: Optional[Mapping[str, Any]] = None,
            key: Optional[str] = None,
            unit: Optional[str] = None,
            use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        Get responses from a given ``url`` appending an ID to each request from a given ``id_list`` i.e. ``{URL}/{ID}``.
        This function executes each URL request individually for each ID.

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param key: The key to reference from each response to get the list of required values.
        :param unit: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item at the given ``key``.
        """
        if unit is None:
            unit = re.sub(r"[-_]+", " ", key) if key is not None else "items"
        unit = unit.casefold().rstrip("s") + "s"
        url = url.rstrip("/")

        if len(id_list) >= 50:  # show progress bar for batches which may take a long time
            id_list = self.get_progress_bar(iterable=id_list, desc=f'Getting {unit}', unit=unit)

        log = [f"{unit.title()}:{len(id_list):>5}"]
        results: List[Any] = [self.get(f"{url}/{id_}", params=params, use_cache=use_cache, log_pad=43, log_extra=log)
                              for id_ in id_list]
        return [r[key] if key else r for r in results]  # extract items on given key

    def _get_item_results_batch(
            self,
            url: str,
            id_list: List[str],
            params: Optional[Mapping[str, Any]] = None,
            key: Optional[str] = None,
            unit: Optional[str] = None,
            use_cache: bool = True,
            limit: int = 50,
    ) -> List[MutableMapping[str, Any]]:
        """
        Get responses from a given ``url`` appending an ID to each request from a given ``id_list`` i.e. ``{URL}/{ID}``.
        This function executes each URL request in batches of IDs based on the given ``batch_size``.
        It passes this chunked list of IDs to the request handler as a set of params in the form:
        ``{'ids': <comma separated list of IDs>}``

        :param url: The base API URL endpoint for the required requests.
        :param id_list: List of IDs to append to the given URL.
        :param params: Extra parameters to add to each request.
        :param key: The key to reference from each response to get the list of required values.
        :param unit: The unit to use for logging. If None, determine from ``key`` or default to ``items``.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :param limit: Size of each batch of IDs to get. This value will be limited to be between ``1`` and
            the object's current ``batch_size_max``. Maximum=50.
        :return: Raw API responses for each item at the given ``key``.
        """
        if unit is None:  # determine the unit type to use in the progress bar
            unit = re.sub(r"[-_]+", " ", key) if key is not None else "items"
        unit = unit.casefold().rstrip("s") + "s"
        url = url.rstrip("/")

        id_chunks = chunk(id_list, size=limit_value(limit, ceil=50))

        bar = range(len(id_chunks))
        if len(id_chunks) >= 10:  # show progress bar for batches which may take a long time
            bar = self.get_progress_bar(iterable=bar, desc=f'Getting {unit}', unit="pages")

        results = []
        params = params if params is not None else {}
        for i, idx in enumerate(bar, 1):  # get responses in batches
            id_chunk = id_chunks[idx]
            params_chunk = params | {'ids': ','.join(id_chunk)}

            log = [f"{unit.title() + ':':<11} {len(results) + len(id_chunk):>6}/{len(id_list):<6}"]
            response = self.get(url, params=params_chunk, use_cache=use_cache, log_pad=43, log_extra=log)
            results.extend(response[key]) if key else results.append(response)
        
        return results

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_items(
            self, values: APIMethodInputType, kind: Optional[ItemType] = None, limit: int = 50, use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s`` - Get information for given list of ``values``. Items may be:
            - A string representing a URL/URI/ID.
            - A collection of strings representing URLs/URIs/IDs of the same type.
            - A Spotify API JSON response for a collection including some items under an ``items`` key,
                a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.
            - A list of Spotify API JSON responses for a collection including some items under an ``items`` key,
                a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.

        If a JSON response is given, this replaces the ``items`` with the new results.

        :param values: The values representing some Spotify items. See description for allowed value types.
            These items must all be of the same type of item i.e. all tracks OR all artists etc.
        :param kind: Item type if given string is ID.
        :param limit: Size of batches to request.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item.
        :raises SpotifyItemTypeError: Raised when the function cannot determine the item type of the input ``values``.
            Or when it does not recognise the type of the input ``values`` parameter.
        """
        if kind is None:  # determine the item type
            kind = get_item_type(values)
        else:
            validate_item_type(values, kind=kind)

        kind_str = f"{kind.name.casefold()}s"
        url = f"{__URL_API__}/{kind_str}"
        id_list = extract_ids(values, kind=kind)

        if kind == ItemType.USER or kind == ItemType.PLAYLIST:
            results = self._get_item_results(url=url, id_list=id_list, unit=kind_str, use_cache=use_cache)
        else:
            results = self._get_item_results_batch(url=url, id_list=id_list, key=kind_str,
                                                   use_cache=use_cache, limit=limit)

        self.logger.debug(f"{'DONE':<7}: {url:<43} | Retrieved {len(results):>6} {kind_str}")

        # if API response was given on input, update it with new responses
        if isinstance(values, dict) and len(results) == 0:
            values.clear()
            values.update(results[0])
        elif isinstance(values, (list, set)) and all(isinstance(item, dict) for item in values):
            values.clear()
            values.extend(results)

        return results

    def get_tracks_extra(
            self,
            values: APIMethodInputType,
            features: bool = False,
            analysis: bool = False,
            limit: int = 50,
            use_cache: bool = True,
    ) -> MutableMapping[str, List[Mapping[str, Any]]]:
        """
        ``GET: /audio-features`` and/or ``GET: /audio-analysis`` - Get audio features/analysis for list of items.
        Items may be:
            * A string representing a URL/URI/ID.
            * A collection of strings representing URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.
            * A list of Spotify API JSON responses for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.

        If a JSON response is given, this updates ``items`` by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        :param values: The values representing some Spotify tracks. See description for allowed value types.
        :param features: When True, get audio features.
        :param analysis: When True, get audio analysis.
        :param limit: Size of batches to request when getting audio features.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item.
        :raises SpotifyItemTypeError: Raised when the item types of the input ``values`` are not all tracks or IDs.
        """
        if not features and not analysis:  # skip on all False
            return {}

        validate_item_type(values, kind=ItemType.TRACK)

        id_list = extract_ids(values, kind=ItemType.TRACK)
        if len(id_list) == 0:  # skip on empty
            self.logger.debug(f"{'SKIP':<7}: {__URL_API__:<43} | No data given")
            return {}

        features_key = "audio_features"
        features_url = f"{__URL_API__}/audio-features"
        analysis_key = "audio_analysis"
        analysis_url = f"{__URL_API__}/audio-analysis"

        results: MutableMapping[str, List[Mapping[str, Any]]] = {}
        if len(id_list) == 1:
            if features:
                results[features_key] = [self.get(f"{features_url}/{id_list[0]}", use_cache=use_cache, log_pad=43)]
            if analysis:
                results[analysis_key] = [self.get(f"{analysis_url}/{id_list[0]}", use_cache=use_cache, log_pad=43)]
        else:
            if features:
                results[features_key] = self._get_item_results_batch(features_url, id_list=id_list, key=features_key,
                                                                     unit="features", use_cache=use_cache,
                                                                     limit=limit)
            if analysis:
                results[analysis_key] = self._get_item_results(url=analysis_url, id_list=id_list,
                                                               unit="analysis", use_cache=use_cache)

        # if API response was given on input, update it with new responses
        if isinstance(values, dict):
            for key, result in results.items():
                values[key] = result[0]
        elif isinstance(values, (list, set)) and all(isinstance(item, dict) and "id" in item for item in values):
            for key, result in results.items():
                result_mapped = {r["id"]: r for r in result}
                for item in values:
                    item[key] = result_mapped[item["id"]]

        return results

    def get_tracks(
            self,
            values: APIMethodInputType,
            features: bool = False,
            analysis: bool = False,
            limit: int = 50,
            use_cache: bool = True
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s`` + GET: /audio-features`` and/or ``GET: /audio-analysis``

        Get audio features/analysis for list of tracks.
        Mostly just a wrapper for ``get_items`` and ``get_tracks`` functions.
        Items may be:
            * A string representing a URL/URI/ID.
            * A collection of strings representing URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.
            * A list of Spotify API JSON responses for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.

        If a JSON response is given, this updates ``items`` by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        :param values: The values representing some Spotify tracks. See description for allowed value types.
        :param features: When True, get audio features.
        :param analysis: When True, get audio analysis.
        :param limit: Size of batches to request when getting audio features.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item.
        :raises SpotifyItemTypeError: Raised when the item types of the input ``tracks`` are not all tracks or IDs.
        """
        tracks = self.get_items(values=values, kind=ItemType.TRACK, limit=limit, use_cache=use_cache)
        self.get_tracks_extra(values=tracks, features=features, analysis=analysis, limit=limit, use_cache=use_cache)
        return tracks
