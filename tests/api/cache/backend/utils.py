import json
from typing import Any

from aiohttp import ClientResponse
from yarl import URL

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings


class MockRequestSettings(RequestSettings):

    @staticmethod
    def get_name(value: Any) -> str | None:
        if isinstance(value, dict):
            return value.get("name")
        elif isinstance(value, ClientResponse):
            try:
                return value.json().get("name")
            except json.decoder.JSONDecodeError:
                pass

    @staticmethod
    def get_id(url: str | URL) -> str | None:
        if str(url).endswith(".com"):
            return
        return URL(url).path.split("/")[-1]


class MockPaginatedRequestSettings(MockRequestSettings, PaginatedRequestSettings):
    @staticmethod
    def get_offset(url: str | URL) -> int:
        params = URL(url).query
        return int(params.get("offset", 0))

    @staticmethod
    def get_limit(url: str | URL) -> int:
        params = URL(url).query
        return int(params.get("limit", 0))
