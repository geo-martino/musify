import re
from abc import ABCMeta
from typing import Optional, List, MutableMapping, Mapping, Any

from syncify.spotify import ItemType, __URL_API__
from syncify.spotify.endpoints.utilities import Utilities, InputItemTypeVar


class Items(Utilities, metaclass=ABCMeta):
    url_log_width = 46
    batch_size_max = 50

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
        unit = unit.lower().rstrip("s") + "s"
        url = url.rstrip("/")

        self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}} | {unit.title()}:{len(id_list):>5}")

        if len(id_list) > 50:  # show progress bar for batches which may take a long time
            id_list = self._get_progress_bar(iterate=id_list, desc=f'Getting {unit}', unit=unit)

        results: List[Any] = [self.requests.get(f"{url}/{id_}", params=params, use_cache=use_cache) for id_ in id_list]
        results = [r[key] if key else r for r in results]
        self._logger.debug(f"{'DONE':<7}: {url:<{self.url_log_width}} | "
                           f"Retrieved data for {len(results):>3} {unit}")
        return results

    def _get_item_results_batched(
            self,
            url: str,
            id_list: List[str],
            params: Optional[Mapping[str, Any]] = None,
            key: Optional[str] = None,
            unit: Optional[str] = None,
            use_cache: bool = True,
            batch_size: int = batch_size_max,
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
        :param batch_size: Size of each batch of IDs to get. This value will be limited to be between ``1`` and
            the object's current ``batch_size_max``. Maximum=50.
        :return: Raw API responses for each item at the given ``key``.
        """
        if unit is None:
            unit = re.sub(r"[-_]+", " ", key) if key is not None else "items"
        unit = unit.lower().rstrip("s") + "s"
        url = url.rstrip("/")

        id_chunks = self.chunk_items(id_list, size=self.limit_value(batch_size))
        self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}} | "
                           f"Pages:{len(id_chunks):>4} | {unit.title()}:{len(id_list):>5}")

        if len(id_chunks) > 10:  # show progress bar for batches which may take a long time
            id_chunks = self._get_progress_bar(iterate=id_chunks, desc=f'Getting {unit}', unit=unit)

        results = []
        params = params if params is not None else {}
        for i, id_chunk in enumerate(id_chunks, 1):
            params_chunk = params | {'ids': ','.join(id_chunk)}
            self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}} | "
                               f"Page :{i:>4} | Params: {params_chunk}")

            response = self.requests.get(url, params=params_chunk, use_cache=use_cache)
            results.extend(response[key]) if key else results.append(response)

        self._logger.debug(f"{'DONE':<7}: {url:<{self.url_log_width}} | "
                           f"Retrieved data for {len(results):>3} {unit}")
        return results

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_items(
            self,
            items: InputItemTypeVar,
            kind: Optional[ItemType] = None,
            batch_size: int = 50,
            use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /{kind}s`` - Get information for given list of ``items``. Items may be:
            * A single string value.
            * A dictionary response from Spotify API represent some item.
            * A list of string values.
            * A list of dictionary responses from Spotify API represent some items.

        :param items: List of items to get. See description.
        :param kind: Item type if given string is ID.
        :param batch_size: Size of batches to request.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when it does not recognise the type of the input ``items`` parameter.
        """
        if kind is None:
            kind = self.get_item_type_from_list(items)

        kind_str = f"{kind.name.lower()}s"
        url = f"{__URL_API__}/{kind_str}"
        id_list = self.extract_ids(items, kind=kind)

        if kind == ItemType.USER or kind == ItemType.PLAYLIST:
            results = self._get_item_results(url=url, id_list=id_list, unit=kind_str, use_cache=use_cache)
        else:
            results = self._get_item_results_batched(
                url=url, id_list=id_list, key=kind_str, use_cache=use_cache, batch_size=batch_size
            )

        return results

    def get_audio_features(
            self, items: InputItemTypeVar, batch_size: int = 50, use_cache: bool = True,
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /audio-features`` - Get audio features for list of items. Items may be:
            * A single string value.
            * A dictionary response from Spotify API represent some item.
            * A list of string values.
            * A list of dictionary responses from Spotify API represent some items.

        :param items: List of items to get. See description.
        :param batch_size: Size of batches to request.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item.
        :exception ValueError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        item_type = self.get_item_type_from_list(items)
        if item_type is not None and not item_type == ItemType.TRACK:
            item_str = "unknown" if item_type is None else item_type.name.lower() + "s"
            raise ValueError(f"Given items must all be track URLs/URIs/IDs, not {item_str}")

        key = "audio_features"
        url = f"{__URL_API__}/{key.replace('_', '-')}"
        id_list = self.extract_ids(items, kind=ItemType.TRACK)

        if len(id_list) == 0:
            self._logger.debug(f"{'SKIP':<7}: {url:<{self.url_log_width}} | No data given")
            return []
        elif len(id_list) == 1:
            self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}} | ID: {id_list[0]}")
            return [self.requests.get(f"{url}/{id_list[0]}")]

        unit = ItemType.TRACK.name
        results = self._get_item_results_batched(
            url=url, id_list=id_list, key=key, unit=unit, use_cache=use_cache, batch_size=batch_size
        )

        if isinstance(items, dict):
            items[key] = results
        elif isinstance(items, list) and all(isinstance(item, dict) and "id" in item for item in items):
            features = {r["id"]: r for r in results}
            for item in items:
                item[key] = features[item["id"]]

        return results

    def get_audio_analysis(
            self, items: InputItemTypeVar, use_cache: bool = True) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /audio-analysis`` - Get audio analyses for track list. Items may be:
            * A single string value.
            * A dictionary response from Spotify API represent some item.
            * A list of string values.
            * A list of dictionary responses from Spotify API represent some items.

        :param items: List of items to get. See description.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: Raw API responses for each item.
        :exception ValueError: Raised when the item types of the input ``items`` are not all tracks or IDs.
        """
        item_type = self.get_item_type_from_list(items)
        if item_type is not None and not item_type == ItemType.TRACK:
            item_str = "unknown" if item_type is None else item_type.name.lower() + "s"
            raise ValueError(f"Given items must all be track URLs/URIs/IDs, not {item_str}")

        key = "audio_analysis"
        url = f"{__URL_API__}/{key.replace('_', '-')}"
        id_list = self.extract_ids(items, kind=ItemType.TRACK)

        url_log = url.format(id_='').rstrip("/")
        if len(id_list) == 0:
            self._logger.debug(f"{'SKIP':<7}: {url_log:<{self.url_log_width}} | No data given")
            return []
        elif len(id_list) == 1:
            self._logger.debug(f"{'GET':<7}: {url_log:<{self.url_log_width}} | ID: {id_list[0]}")
            return [self.requests.get(url.format(id_=id_list[0]))]

        results = self._get_item_results(url=url, id_list=id_list, unit=ItemType.TRACK.name, use_cache=use_cache)
        if isinstance(items, dict):
            items[key] = results
        elif isinstance(items, list) and all(isinstance(item, dict) and "id" in item for item in items):
            analysis = {r["id"]: r for r in results}
            for item in items:
                item[key] = analysis[item["id"]]

        return results
