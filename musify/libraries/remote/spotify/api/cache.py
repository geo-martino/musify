from http import HTTPMethod
from typing import Any

from aiorequestful.cache.backend.base import ResponseRepositorySettings
from aiorequestful.types import MethodInput, URLInput
from yarl import URL

from musify.libraries.remote.core.exception import RemoteObjectTypeError
from musify.libraries.remote.core.types import RemoteIDType
from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler


class SpotifyRepositorySettings(ResponseRepositorySettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return "id",

    def get_key(self, method: MethodInput, url: URLInput, **__) -> tuple[str | None, ...]:
        if HTTPMethod(method) != HTTPMethod.GET:
            return (None,)

        try:
            return SpotifyDataWrangler.convert(str(url), type_in=RemoteIDType.URL, type_out=RemoteIDType.ID),
        except RemoteObjectTypeError:
            pass
        return (None,)

    def get_name(self, payload: dict[str, Any]) -> str | None:
        if payload.get("type") == "user":
            return payload["display_name"]
        return payload.get("name")


class SpotifyPaginatedRepositorySettings(SpotifyRepositorySettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return *super().fields, "offset", "size"

    def get_key(self, method: MethodInput, url: URLInput, **__) -> tuple[str | int | None, ...]:
        base = super().get_key(method=method, url=url)
        return *base, self.get_offset(url), self.get_limit(url)

    @staticmethod
    def get_offset(url: URLInput) -> int:
        """Extracts the offset for a paginated request from the given ``url``."""
        params = URL(url).query
        return int(params.get("offset", 0))

    @staticmethod
    def get_limit(url: URLInput) -> int:
        """Extracts the limit for a paginated request from the given ``url``."""
        params = URL(url).query
        return int(params.get("limit", 50))
