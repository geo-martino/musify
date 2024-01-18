"""
Convert and validate Spotify ID and item types.
"""

from collections.abc import Mapping, Collection
from typing import Any
from urllib.parse import urlparse

from musify.shared.exception import MusifyEnumError
from musify.shared.remote.api import APIMethodInputType
from musify.shared.remote.enum import RemoteIDType, RemoteObjectType
from musify.shared.remote.exception import RemoteError, RemoteIDTypeError, RemoteObjectTypeError
from musify.shared.remote.processors.wrangle import RemoteDataWrangler
from musify.spotify import URL_API, URL_EXT, SPOTIFY_UNAVAILABLE_URI, SpotifyRemote


class SpotifyDataWrangler(RemoteDataWrangler, SpotifyRemote):

    unavailable_uri_dummy = SPOTIFY_UNAVAILABLE_URI

    @staticmethod
    def get_id_type(value: str, kind: RemoteObjectType | None = None) -> RemoteIDType:
        value = value.strip().casefold()
        uri_split = value.split(':')

        if value.startswith(URL_API):
            return RemoteIDType.URL
        elif value.startswith(URL_EXT):
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
            return value.startswith(URL_API)
        elif kind == RemoteIDType.URL_EXT:
            return value.startswith(URL_EXT)
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

    @staticmethod
    def _get_item_type(value: str | Mapping[str, Any], kind: RemoteObjectType) -> RemoteObjectType | None:
        if isinstance(value, Mapping):
            if value.get("is_local", False):
                raise RemoteObjectTypeError("Cannot process local items")
            if "type" not in value:
                raise RemoteObjectTypeError(f"Given map does not contain a 'type' key: {value}")
            return RemoteObjectType.from_name(value["type"].casefold().rstrip('s'))[0]

        value = value.strip()
        uri_check = value.split(':')

        if value.startswith(URL_API) or value.startswith(URL_EXT):  # open/API URL
            value = value.removeprefix(URL_API) if value.startswith(URL_API) else value.removeprefix(URL_EXT)
            url_path = urlparse(value).path.split("/")
            for chunk in url_path:
                try:
                    return RemoteObjectType.from_name(chunk.casefold().rstrip('s'))[0]
                except MusifyEnumError:
                    continue
        elif len(uri_check) == RemoteIDType.URI.value and uri_check[0].casefold() == "spotify":
            return RemoteObjectType.from_name(uri_check[1])[0]
        elif len(value) == RemoteIDType.ID.value or kind == RemoteObjectType.USER:
            return kind
        raise RemoteObjectTypeError(f"Could not determine item type of given value: {value}")

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

        if type_in == RemoteIDType.URL_EXT or type_in == RemoteIDType.URL:  # open/API URL
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

        elif type_in == RemoteIDType.URI:
            uri_split = value.split(':')
            kind = RemoteObjectType.from_name(uri_split[1])[0]
            id_ = uri_split[2]

        elif type_in == RemoteIDType.ID:
            if kind is None:
                raise RemoteIDTypeError("Input value is an ID and no defined 'kind' has been given.", RemoteIDType.ID)
            id_ = value

        else:
            raise RemoteIDTypeError(f"Could not determine item type: {value}")

        # reformat
        item = kind.name.lower().rstrip('s')
        if type_out == RemoteIDType.URL:
            return f'{URL_API}/{item}s/{id_}'
        elif type_out == RemoteIDType.URL_EXT:
            return f'{URL_EXT}/{item}/{id_}'
        elif type_out == RemoteIDType.URI:
            return f"spotify:{item}:{id_}"
        else:
            return id_

    @classmethod
    def extract_ids(cls, values: APIMethodInputType, kind: RemoteObjectType | None = None) -> list[str]:
        if isinstance(values, str):
            return [cls.convert(values, kind=kind, type_out=RemoteIDType.ID)]
        elif isinstance(values, Mapping) and "id" in values:  # is a raw API response from Spotify
            return [values["id"]]
        elif isinstance(values, Collection):
            if len(values) == 0:
                return []
            elif all(isinstance(d, str) for d in values):
                return [cls.convert(d, kind=kind, type_out=RemoteIDType.ID) for d in values]
            elif all(isinstance(d, Mapping) and "id" in d for d in values):
                return [track["id"] for track in values]

        raise RemoteError(f"Could not extract IDs. Input data not recognised: {type(values)}")
