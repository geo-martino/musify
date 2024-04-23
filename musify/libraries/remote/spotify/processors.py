"""
Convert and validate Spotify ID and item types.
"""
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from musify.exception import MusifyEnumError
from musify.libraries.core.collection import MusifyCollection
from musify.libraries.remote.core import RemoteResponse
from musify.libraries.remote.core.api import APIInputValue
from musify.libraries.remote.core.enum import RemoteIDType, RemoteObjectType
from musify.libraries.remote.core.exception import RemoteError, RemoteIDTypeError, RemoteObjectTypeError
from musify.libraries.remote.core.processors.wrangle import RemoteDataWrangler
from musify.libraries.remote.spotify import SOURCE_NAME
from musify.utils import to_collection


class SpotifyDataWrangler(RemoteDataWrangler):

    source = SOURCE_NAME
    unavailable_uri_dummy = "spotify:track:unavailable"
    url_api = "https://api.spotify.com/v1"
    url_ext = "https://open.spotify.com"

    @classmethod
    def get_id_type(cls, value: str, kind: RemoteObjectType | None = None) -> RemoteIDType:
        value = value.strip().casefold()
        uri_split = value.split(':')

        if value.startswith(cls.url_api):
            return RemoteIDType.URL
        elif value.startswith(cls.url_ext):
            return RemoteIDType.URL_EXT
        elif len(uri_split) == RemoteIDType.URI.value and uri_split[0] == "spotify":  # URI
            if uri_split[1] == "user":
                return RemoteIDType.URI
            elif uri_split[1] != "user" and len(uri_split[2]) == RemoteIDType.ID.value:
                return RemoteIDType.URI
        elif len(value) == RemoteIDType.ID.value or kind == RemoteObjectType.USER:
            return RemoteIDType.ID
        raise RemoteIDTypeError(f"Could not determine ID type of given value: {value}")

    @classmethod
    def validate_id_type(cls, value: str, kind: RemoteIDType = RemoteIDType.ALL) -> bool:
        value = value.strip().casefold()

        if kind == RemoteIDType.URL:
            return value.startswith(cls.url_api)
        elif kind == RemoteIDType.URL_EXT:
            return value.startswith(cls.url_ext)
        elif kind == RemoteIDType.URI:
            uri_split = value.split(':')
            if len(uri_split) != RemoteIDType.URI.value or uri_split[0] != "spotify":
                return False
            return uri_split[1] == "user" or (uri_split[1] != "user" and len(uri_split[2]) == RemoteIDType.ID.value)
        elif kind == RemoteIDType.ID:
            return len(value) == RemoteIDType.ID.value
        elif kind == RemoteIDType.ALL:
            try:
                cls.get_id_type(value)
                return True
            except RemoteIDTypeError:
                pass
        return False

    @classmethod
    def _get_item_type(
            cls, value: str | Mapping[str, Any] | RemoteResponse, kind: RemoteObjectType | None = None
    ) -> RemoteObjectType | None:
        if isinstance(value, RemoteResponse):
            return cls._get_item_type_from_response(value)
        if isinstance(value, Mapping):
            return cls._get_item_type_from_mapping(value)

        value = value.strip()
        uri_check = value.split(':')

        if value.startswith(cls.url_api) or value.startswith(cls.url_ext):  # open/API URL
            value = value.removeprefix(cls.url_api if value.startswith(cls.url_api) else cls.url_ext)
            url_path = urlparse(value).path.split("/")
            for chunk in url_path:
                try:
                    return RemoteObjectType.from_name(chunk.casefold().rstrip('s'))[0]
                except MusifyEnumError:
                    continue
        elif len(uri_check) == RemoteIDType.URI.value and uri_check[0].casefold() == "spotify":
            return RemoteObjectType.from_name(uri_check[1])[0]
        elif len(value) == RemoteIDType.ID.value or kind == RemoteObjectType.USER:
            # in these cases, we have to go on faith...
            return kind
        raise RemoteObjectTypeError(f"Could not determine item type of given value: {value}")

    @classmethod
    def _get_item_type_from_response(cls, value: RemoteResponse) -> RemoteObjectType:
        response_kind = cls._get_item_type_from_mapping(value.response)
        if value.kind != response_kind:
            raise RemoteObjectTypeError(
                f"RemoteResponse kind != actual response kind: {value.kind} != {response_kind}"
            )
        return value.kind

    @classmethod
    def _get_item_type_from_mapping(cls, value: Mapping[str, Any]) -> RemoteObjectType:
        if value.get("is_local", False):
            raise RemoteObjectTypeError("Cannot process local items")
        if "type" not in value:
            raise RemoteObjectTypeError(f"Given map does not contain a 'type' key: {value}")
        return RemoteObjectType.from_name(value["type"].casefold().rstrip('s'))[0]

    @classmethod
    def convert(
            cls,
            value: str,
            kind: RemoteObjectType | None = None,
            type_in: RemoteIDType = RemoteIDType.ALL,
            type_out: RemoteIDType = RemoteIDType.ID
    ) -> str:
        if cls.validate_id_type(value, kind=type_out):
            return value
        if type_in == RemoteIDType.ALL or not cls.validate_id_type(value, kind=type_in):
            type_in = cls.get_id_type(value, kind=kind)

        value = value.strip()

        if type_in == RemoteIDType.URL_EXT or type_in == RemoteIDType.URL:
            kind, id_ = cls._get_id_from_url(value=value, kind=kind)
        elif type_in == RemoteIDType.URI:
            kind, id_ = cls._get_id_from_uri(value=value)
        elif type_in == RemoteIDType.ID:
            if kind is None:
                raise RemoteIDTypeError("Input value is an ID and no defined 'kind' has been given.", RemoteIDType.ID)
            id_ = value
        else:
            raise RemoteIDTypeError(f"Could not determine item type: {value}")

        # reformat
        item = kind.name.lower().rstrip('s')
        if type_out == RemoteIDType.URL:
            return f'{cls.url_api}/{item}s/{id_}'
        elif type_out == RemoteIDType.URL_EXT:
            return f'{cls.url_ext}/{item}/{id_}'
        elif type_out == RemoteIDType.URI:
            return f"spotify:{item}:{id_}"
        else:
            return id_

    @classmethod
    def _get_id_from_url(cls, value: str, kind: RemoteObjectType | None = None) -> tuple[RemoteObjectType, str]:
        url_path = urlparse(value).path.split("/")
        for chunk in url_path:
            try:
                kind = RemoteObjectType.from_name(chunk.rstrip('s'))[0]
                break
            except MusifyEnumError:
                continue

        if kind == RemoteObjectType.USER:
            name = kind.name.lower()
            try:
                id_ = url_path[url_path.index(name) + 1]
            except ValueError:
                id_ = url_path[url_path.index(name + "s") + 1]
        else:
            id_ = next(p for p in url_path if len(p) == RemoteIDType.ID.value)

        return kind, id_

    @classmethod
    def _get_id_from_uri(cls, value: str) -> tuple[RemoteObjectType, str]:
        uri_split = value.split(':')
        kind = RemoteObjectType.from_name(uri_split[1])[0]
        id_ = uri_split[2]
        return kind, id_

    @classmethod
    def extract_ids(cls, values: APIInputValue, kind: RemoteObjectType | None = None) -> list[str]:
        def extract_id(value: str | Mapping[str, Any] | RemoteResponse) -> str:
            """Extract an ID from a given ``value``"""
            if isinstance(value, str):
                return cls.convert(value, kind=kind, type_out=RemoteIDType.ID)
            elif isinstance(value, Mapping) and "id" in value:
                return value["id"]
            elif isinstance(value, RemoteResponse):
                return value.id

            raise RemoteError(f"Could not extract ID. Input data not recognised: {type(value)}")

        values = to_collection(values) if not isinstance(values, MusifyCollection) else [values]
        return [extract_id(value=value) for value in to_collection(values)]
