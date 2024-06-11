from typing import Any

from yarl import URL

from musify.api.cache.backend.base import RequestSettings
from musify.libraries.remote.core.enum import RemoteIDType
from musify.libraries.remote.core.exception import RemoteObjectTypeError
from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler


class SpotifyRequestSettings(RequestSettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return "id",

    def get_key(self, url: str | URL, *_, **__) -> tuple[str | None, ...]:
        try:
            return SpotifyDataWrangler.convert(str(url), type_in=RemoteIDType.URL, type_out=RemoteIDType.ID),
        except RemoteObjectTypeError:
            pass
        return (None,)

    @staticmethod
    def get_name(response: dict[str, Any]) -> str | None:
        if response.get("type") == "user":
            return response["display_name"]
        return response.get("name")


class SpotifyPaginatedRequestSettings(SpotifyRequestSettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return *super().fields, "offset", "size"

    def get_key(self, url: str | URL, *_, **__) -> tuple[str | int | None, ...]:
        base = super().get_key(url=url)
        return *base, self.get_offset(url), self.get_limit(url)

    @staticmethod
    def get_offset(url: str | URL) -> int:
        """Extracts the offset for a paginated request from the given ``url``."""
        params = URL(url).query
        return int(params.get("offset", 0))

    @staticmethod
    def get_limit(url: str | URL) -> int:
        """Extracts the limit for a paginated request from the given ``url``."""
        params = URL(url).query
        return int(params.get("limit", 50))
