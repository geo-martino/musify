import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from requests import Response

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings


class MockRequestSettings(RequestSettings):

    @staticmethod
    def get_name(value: Any) -> str | None:
        if isinstance(value, dict):
            return value.get("name")
        elif isinstance(value, Response):
            try:
                return value.json().get("name")
            except json.decoder.JSONDecodeError:
                pass

    @staticmethod
    def get_id(url: str) -> str | None:
        if "/" not in url:
            return
        return urlparse(url).path.split("/")[-1]


class MockPaginatedRequestSettings(MockRequestSettings, PaginatedRequestSettings):
    @staticmethod
    def get_offset(url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("offset", [0])[0])

    @staticmethod
    def get_limit(url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("size", [0])[0])
