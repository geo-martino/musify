from aiohttp.typedefs import StrOrURL

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
    def get_id(url: StrOrURL) -> str | None:
        try:
            return SpotifyDataWrangler.convert(str(url), type_in=RemoteIDType.URL, type_out=RemoteIDType.ID)
        except RemoteObjectTypeError:
            pass


class SpotifyPaginatedRequestSettings(PaginatedRequestSettings, SpotifyRequestSettings):

    @classmethod
    def get_offset(cls, url: StrOrURL) -> int:
        params = cls._get_params(url)
        return int(params.get("offset", 0))

    @classmethod
    def get_limit(cls, url: StrOrURL) -> int:
        params = cls._get_params(url)
        return int(params.get("limit", [50])[0])
