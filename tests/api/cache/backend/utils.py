import json
from typing import Any
from urllib.parse import urlparse

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
        path = url.path if isinstance(url, URL) else urlparse(url).path
        return path.split("/")[-1]


class MockPaginatedRequestSettings(MockRequestSettings, PaginatedRequestSettings):
    @classmethod
    def get_offset(cls, url: str | URL) -> int:
        params = cls._get_params(url)
        return int(params.get("offset", 0))

    @classmethod
    def get_limit(cls, url: str | URL) -> int:
        params = cls._get_params(url)
        return int(params.get("limit", 0))
