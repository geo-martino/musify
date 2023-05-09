from abc import ABCMeta, abstractmethod
from typing import Optional, List, Union, MutableMapping, Any
from urllib.parse import urlparse

from syncify.api.request import RequestHandler
from syncify.spotify import IDType, ItemType, __URL_API__, __URL_OPEN__
from syncify.utils.logger import Logger
from utils_new.exception import EnumNotFoundError

InputItemTypeVar = Union[str, MutableMapping[str, Any], List[str], List[MutableMapping[str, Any]]]


class Utilities(Logger, metaclass=ABCMeta):
    url_log_width = 46  # for aligning the URLs when logging
    batch_size_max = 50  # max batch size for batchable endpoints

    @property
    @abstractmethod
    def requests(self) -> RequestHandler:
        """Requests handler"""
        raise NotImplementedError

    @property
    @abstractmethod
    def user_id(self) -> Optional[str]:
        """ID of the currently authenticated used"""
        raise NotImplementedError

    @staticmethod
    def limit_value(value: int, floor: int = 1, ceil: int = batch_size_max) -> int:
        """Limits a given ``value`` to always be between some ``floor`` and ``ceil``"""
        return max(min(value, ceil), floor)

    @staticmethod
    def chunk_items(values: List[Any], size: int) -> List[List[Any]]:
        """Chunks a list of ``values`` into a list of lists of equal ``size``"""
        return [values[i: i + size] for i in range(0, len(values), size) if len(values[i: i + size]) > 0]

    @staticmethod
    def validate_id_type(value: str, kind: IDType) -> bool:
        """Check that a given ``value`` is a type of Spotify ID given by ``kind ``"""
        value = value.strip().lower()

        if kind == IDType.URL_API:
            return value.startswith(__URL_API__)
        elif kind == IDType.URL_OPEN:
            return value.startswith(__URL_OPEN__)
        elif kind == IDType.URI:
            uri_split = value.split(':')
            return len(uri_split) == IDType.URI.value and uri_split[0] == "spotify"
        elif kind == IDType.ID:
            return len(value) == IDType.ID.value
        return False

    @staticmethod
    def get_id_type(value: str) -> IDType:
        """
        Determine the Spotify ID type of the given ``value`` and return its type.

        :param value: A string to determine.
        :returns: The Spotify ID type.
        :exception ValueError: Raised when the function cannot determine the ID type of the input ``items``.
        """
        value = value.strip().lower()
        url_check = [i for i in urlparse(value.replace('/v1/', '/')).netloc.split(".") if i]
        uri_check = value.split(':')

        if len(url_check) > 0:
            if url_check[0] == 'api':  # open/api url
                return IDType.URL_API
            elif url_check[0] == 'open':
                return IDType.URL_OPEN
        elif len(uri_check) == IDType.URI.value:
            return IDType.URI
        elif len(value) == IDType.ID.value:  # use manually defined kind for a given id
            return IDType.ID
        raise ValueError(f"Could not determine ID type of given value: {value}")

    @staticmethod
    def get_item_type(value: Union[str, MutableMapping[str, Any]]) -> Optional[ItemType]:
        """
        Determine the Spotify item type of the given ``value`` and return its type.

        :param value: A string to determine or some dictionary response from the Spotify API.
        :returns: The Spotify item type. If the given value is determined to be an ID, returns None.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
        """
        if isinstance(value, dict):
            if "type" in value:
                return ItemType.from_name(value["type"].rstrip('s'))
            raise ValueError(f"Given map does not contain a 'type' key: {value}")

        value = value.strip()
        url_check = urlparse(value.replace('/v1/', '/')).netloc.split(".")
        uri_check = value.split(':')

        if len(url_check) > 0 and url_check[0] == 'open' or url_check[0] == 'api':  # open/api url
            url_path = urlparse(value.replace('/v1/', '/')).path.split("/")
            for chunk in url_path:
                try:
                    return ItemType.from_name(chunk.rstrip('s'))
                except EnumNotFoundError:
                    continue
        elif len(uri_check) == IDType.URI.value:
            return ItemType.from_name(uri_check[1])
        elif len(value) == IDType.ID.value:  # use manually defined kind for a given id
            return None
        raise ValueError(f"Could not determine item type of given value: {value}")

    def get_item_type_from_list(self, values: List[str]) -> ItemType:
        """
        Determine the Spotify item type from a list of ``values``

        :param values: A list of strings to determine.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when the list contains strings representing many differing Spotify item types or only IDs.
        """
        kinds = {self.get_item_type(value) for value in values}
        kinds = [kind for kind in kinds if kind is not None]
        if len(kinds) == 0:
            raise ValueError("Given items are invalid or are IDs with no kind given")
        if len(kinds) != 1:
            raise ValueError(f"Ensure all the given items are of the same type! Found: {kinds}")
        return kinds[0]

    def convert(
            self,
            value: str,
            kind: Optional[ItemType] = None,
            type_in: Optional[IDType] = None,
            type_out: Optional[IDType] = None
    ) -> str:
        """
        Converts ID to required format - API URL, OPEN URL, URI, or ID.

        :param value: URL/URI/ID to convert.
        :param kind: Optionally, give the item type of the input ``value`` to reduce skip some checks.
            This is required when the given ``value`` is an ID.
        :param type_in: Optionally, give the ID type of the input ``value`` to reduce skip some checks.
        :param type_out: Optionally, give the ID type of the output ``value``. Returns the ID when None.
        :return: Formatted string.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
        """
        value = value.strip()
        if type_in is None or type_in == IDType.ALL or not self.validate_id_type(value, kind=type_in):
            type_in = self.get_id_type(value)

        if type_in == IDType.URL_OPEN or type_in == IDType.URL_API:  # open/api url
            url_path = urlparse(value.strip()).path.split("/")
            for chunk in url_path:
                try:
                    kind = ItemType.from_name(chunk.rstrip('s'))
                    break
                except EnumNotFoundError:
                    continue
            if kind == ItemType.USER:
                id_ = url_path[url_path.index(kind.name.lower()) + 1]
            else:
                id_ = [p for p in url_path if len(p) == IDType.ID.value][0]
        elif type_in == IDType.URI:
            uri_split = value.split(':')
            kind = ItemType.from_name(uri_split[1])
            id_ = uri_split[2]
        elif type_in == IDType.ID:
            if kind is None:
                raise ValueError("Input value is an ID and no defined 'kind' has been given.")
            id_ = value
        else:
            raise ValueError(f"Could not determine item type: {value}")

        # reformat
        item = kind.name.lower().rstrip('s')
        if type_out == IDType.URL_API:
            return f'{__URL_API__}/{item}s/{id_}'
        elif type_out == IDType.URL_OPEN:
            return f'{__URL_OPEN__}/{item}/{id_}'
        elif type_out == IDType.URI:
            return f'spotify:{item}:{id_}'
        else:
            return id_

    def extract_ids(self, items: InputItemTypeVar, kind: Optional[ItemType] = None) -> List[str]:
        """
        Extract a list of IDs from input ``items``. Items may be:
            * A single string value.
            * A dictionary response from Spotify API represent some item.
            * A list of string values.
            * A list of dictionary responses from Spotify API represent some items.

        :param items: List of items to get. See description.
        :param kind: Optionally, give the item type of the input ``value`` to reduce skip some checks.
            This is required when the given ``value`` is an ID.
        :return: List of IDs.
        :exception ValueError: Raised when the function cannot determine the item type of the input ``items``.
            Or when it does not recognise the type of the input ``items`` parameter.
        """
        if isinstance(items, str):
            return [self.convert(items, kind=kind, type_out=IDType.ID)]
        elif isinstance(items, dict) and 'id' in items:  # is a raw API response from Spotify
            return [items['id']]
        elif isinstance(items, list):
            if len(items) == 0:
                return []
            elif all(isinstance(d, str) for d in items):
                return [self.convert(d, kind=kind, type_out=IDType.ID) for d in items]
            elif all(isinstance(d, dict) and 'id' in d for d in items):
                return [track['id'] for track in items]

        raise ValueError(f"Could not extract IDs. Input data not recognised: {type(items)}")
