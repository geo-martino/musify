from collections.abc import Mapping, Sequence, Container
from typing import Any
from urllib.parse import urlparse

from syncify.enums import EnumNotFoundError
from syncify.spotify import __URL_API__, __URL_EXT__
from syncify.spotify.api import APIMethodInputType
from syncify.spotify.enums import IDType, ItemType
from syncify.spotify.exception import SpotifyError, SpotifyIDTypeError, SpotifyItemTypeError
from syncify.utils import UnitIterable
from syncify.utils.helpers import to_collection


def check_spotify_type(value: str, types: UnitIterable[IDType] = IDType.ALL) -> IDType | None:
    """
    Check that the given value is of a valid Spotify type.

    :param value: URL/URI/ID to check.
    :param types: Spotify types to check for. None checks all.
    :return: The Spotify type if value is valid, None if invalid.
    """
    if not isinstance(value, str):
        return

    types: Container[IDType] = to_collection(types, set)
    if IDType.ALL in types:
        types = set(IDType.all())

    if IDType.URL in types and value.lower().startswith(__URL_API__):
        return IDType.URL
    elif IDType.URL_EXT in types and value.lower().startswith(__URL_EXT__):
        return IDType.URL_EXT
    elif IDType.URI in types and len(value.split(":")) == IDType.URI.value:
        uri_list = value.split(":")
        if not uri_list[0] == "spotify":
            return None
        elif uri_list[1] == "user":
            return IDType.URI
        elif uri_list[1] != "user" and len(uri_list[2]) == IDType.ID.value:
            return IDType.URI
    elif IDType.ID in types and len(value) == IDType.ID.value:
        return IDType.ID


def get_id_type(value: str) -> IDType:
    """
    Determine the Spotify ID type of the given ``value`` and return its type.

    :param value: URL/URI/ID to check.
    :returns: The Spotify ID type.
    :raises SpotifyIDTypeError: Raised when the function cannot determine the ID type of the input ``value``.
    """
    value = value.strip().casefold()
    url_check = tuple(i for i in urlparse(value).netloc.split(".") if i)
    uri_check = value.split(':')

    if len(url_check) > 0:
        if url_check[0] == "api":  # open/api URL
            return IDType.URL
        elif url_check[0] == "open":
            return IDType.URL_EXT
    elif len(uri_check) == IDType.URI.value:
        return IDType.URI
    elif len(value) == IDType.ID.value:  # use manually defined kind for a given id
        return IDType.ID
    raise SpotifyIDTypeError(f"Could not determine ID type of given value: {value}")


def validate_id_type(value: str, kind: IDType) -> bool:
    """Check that the given ``value`` is a type of Spotify ID given by ``kind ``"""
    value = value.strip().casefold()

    if kind == IDType.URL:
        return value.startswith(__URL_API__)
    elif kind == IDType.URL_EXT:
        return value.startswith(__URL_EXT__)
    elif kind == IDType.URI:
        uri_split = value.split(':')
        return len(uri_split) == IDType.URI.value and uri_split[0] == "spotify"
    elif kind == IDType.ID:
        return len(value) == IDType.ID.value
    return False


def get_item_type(values: APIMethodInputType) -> ItemType:
    """
    Determine the Spotify item type of ``values``. Values may be:
        * A string representing a URL/URI.
        * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
        * A Spotify API JSON response for a collection with a valid item type value under a ``type`` key.
        * A MutableSequence of Spotify API JSON responses for a collection with
            a valid type value under a ``type`` key.

    :param values: The values representing some Spotify items. See description for allowed value types.
        These items must all be of the same type of item to pass i.e. all tracks OR all artists etc.
    :raises SpotifyItemTypeError: Raised when the function cannot determine the item type of the input ``values``.
        Or when the list contains strings representing many differing Spotify item types or only IDs.
    """
    if isinstance(values, str) or isinstance(values, Mapping):
        return __get_item_type(values)

    if len(values) == 0:
        raise SpotifyItemTypeError("No values given: collection is empty")

    kinds = {__get_item_type(value) for value in values if value is not None}
    kinds.discard(None)
    if len(kinds) == 0:
        raise SpotifyItemTypeError("Given items are invalid or are IDs with no kind given")
    if len(kinds) != 1:
        raise SpotifyItemTypeError(f"Ensure all the given items are of the same type! Found", value=kinds)
    return kinds.pop()


def __get_item_type(value: str | Mapping[str, Any]) -> ItemType | None:
    """
    Determine the Spotify item type of the given ``value`` and return its type. Value may be:
        * A string representing a URL/URI/ID.
        * A Spotify API JSON response for a collection with a valid item type value under a ``type`` key.

    :param value: The value representing some Spotify item. See description for allowed value types.
    :returns: The Spotify item type. If the given value is determined to be an ID, returns None.
    :raises SpotifyItemTypeError: Raised when the function cannot determine the item type of the input ``values``.
    :raises EnumNotFoundError: Raised when the item type of teh given ``value`` is not a valid Spotify item type.
    """
    if isinstance(value, Mapping):
        if value.get("is_local", False):
            raise SpotifyItemTypeError("Cannot process local items")
        if "type" not in value:
            raise SpotifyItemTypeError(f"Given map does not contain a 'type' key: {value}")
        return ItemType.from_name(value["type"].casefold().rstrip('s'))

    value = value.strip()
    url_check = urlparse(value.replace("/v1/", '/')).netloc.split(".")
    uri_check = value.split(':')

    if len(url_check) > 0 and url_check[0] == "open" or url_check[0] == "api":  # open/api URL
        url_path = urlparse(value.replace("/v1/", '/')).path.split("/")
        for chunk in url_path:
            try:
                return ItemType.from_name(chunk.casefold().rstrip('s'))
            except EnumNotFoundError:
                continue
    elif len(uri_check) == IDType.URI.value and uri_check[0].casefold() == "spotify":
        return ItemType.from_name(uri_check[1])
    elif len(value) == IDType.ID.value:
        return None
    raise SpotifyItemTypeError(f"Could not determine item type of given value: {value}")


def validate_item_type(values: APIMethodInputType, kind: ItemType) -> None:
    """
    Check that the given ``values`` is a type of item given by ``kind `` or a simple ID. Values may be:
        * A string representing a URL/URI/ID.
        * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
        * A Spotify API JSON response for a collection with a valid item type value under a ``type`` key.
        * A MutableSequence of Spotify API JSON responses for a collection with
            a valid type value under a ``type`` key.

    :param values: The values representing some Spotify items. See description for allowed value types.
        These items must all be of the same type of item to pass i.e. all tracks OR all artists etc.
    :param kind: The Spotify item type to check for.
    :raises SpotifyItemTypeError: Raised when the function cannot validate the item type of the input ``values``
        is of type ``kind`` or a simple ID.
    """
    item_type = get_item_type(values)
    if item_type is not None and not item_type == kind:
        item_str = "unknown" if item_type is None else item_type.name.casefold() + "s"
        raise SpotifyItemTypeError(f"Given items must all be {kind.name.casefold()} URLs/URIs/IDs, not {item_str}")


def convert(
        value: str, kind: ItemType | None = None, type_in: IDType = IDType.ALL, type_out: IDType = IDType.ID
) -> str:
    """
    Converts ID to required format - API URL, EXT URL, URI, or ID.

    :param value: URL/URI/ID to convert.
    :param kind: Optionally, give the item type of the input ``value`` to skip some checks.
        This is required when the given ``value`` is an ID.
    :param type_in: Optionally, give the ID type of the input ``value`` to skip some checks.
    :param type_out: The ID type of the output ``value``.
    :return: Formatted string.
    :raises SpotifyIDTypeError: Raised when the function cannot determine the item type of the input ``value``.
    """
    if validate_id_type(value, kind=type_out):
        return value
    if type_in == IDType.ALL or not validate_id_type(value, kind=type_in):
        type_in = get_id_type(value)

    value = value.strip()

    if type_in == IDType.URL_EXT or type_in == IDType.URL:  # open/api URL
        url_path = urlparse(value).path.split("/")
        for chunk in url_path:
            try:
                kind = ItemType.from_name(chunk.rstrip('s'))
                break
            except EnumNotFoundError:
                continue
        if kind == ItemType.USER:
            id_ = url_path[url_path.index(kind.name.casefold()) + 1]
        else:
            id_ = next(p for p in url_path if len(p) == IDType.ID.value)
    elif type_in == IDType.URI:
        uri_split = value.split(':')
        kind = ItemType.from_name(uri_split[1])
        id_ = uri_split[2]
    elif type_in == IDType.ID:
        if kind is None:
            raise SpotifyIDTypeError("Input value is an ID and no defined 'kind' has been given.", IDType.ID)
        id_ = value
    else:
        raise SpotifyIDTypeError(f"Could not determine item type: {value}")

    # reformat
    item = kind.name.casefold().rstrip('s')
    if type_out == IDType.URL:
        return f'{__URL_API__}/{item}s/{id_}'
    elif type_out == IDType.URL_EXT:
        return f'{__URL_EXT__}/{item}/{id_}'
    elif type_out == IDType.URI:
        return f"spotify:{item}:{id_}"
    else:
        return id_


def extract_ids(values: APIMethodInputType, kind: ItemType | None = None) -> list[str]:
    """
    Extract a list of IDs from input ``values``. Items may be:
        * A string representing a URL/URI/ID.
        * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
        * A Spotify API JSON response for a collection with a valid ID value under an ``id`` key.
        * A MutableSequence of Spotify API JSON responses for a collection with
             a valid ID value under an ``id`` key.

    :param values: The values representing some Spotify items. See description for allowed value types.
        These items may be of mixed item types e.g. some tracks AND some artists.
    :param kind: Optionally, give the item type of the input ``value`` to skip some checks.
        This is required when the given ``value`` is an ID.
    :return: List of IDs.
    :raises SpotifyError: Raised when the function cannot determine the item type of the input ``values``.
        Or when it does not recognise the type of the input ``values`` parameter.
    """
    if isinstance(values, str):
        return [convert(values, kind=kind, type_out=IDType.ID)]
    elif isinstance(values, Mapping) and "id" in values:  # is a raw API response from Spotify
        return [values["id"]]
    elif isinstance(values, Sequence):
        if len(values) == 0:
            return []
        elif all(isinstance(d, str) for d in values):
            return [convert(d, kind=kind, type_out=IDType.ID) for d in values]
        elif all(isinstance(d, Mapping) and "id" in d for d in values):
            return [track["id"] for track in values]

    raise SpotifyError(f"Could not extract IDs. Input data not recognised: {type(values)}")
