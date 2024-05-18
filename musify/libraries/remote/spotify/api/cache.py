from urllib.parse import urlparse, parse_qs

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings
from musify.libraries.remote.core.enum import RemoteIDType
from musify.libraries.remote.core.exception import RemoteObjectTypeError
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler


class SpotifyRequestSettings(RequestSettings):

    @staticmethod
    def get_name(value: dict) -> str | None:
        if isinstance(value, dict):
            if value.get("type") == "user":
                return value["display_name"]
            return value.get("name")

    @staticmethod
    def get_id(url: str) -> str | None:
        try:
            return SpotifyDataWrangler.convert(url, type_in=RemoteIDType.URL, type_out=RemoteIDType.ID)
        except RemoteObjectTypeError:
            pass


class SpotifyPaginatedRequestSettings(PaginatedRequestSettings, SpotifyRequestSettings):

    @staticmethod
    def get_offset(url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("offset", [0])[0])

    @staticmethod
    def get_limit(url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("limit", [50])[0])
