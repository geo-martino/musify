import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from aiohttp.typedefs import StrOrURL
from requests import Response
from yarl import URL

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
    def get_id(url: StrOrURL) -> str | None:
        if str(url).endswith(".com"):
            return
        path = url.path if isinstance(url, URL) else urlparse(url).path
        return path.split("/")[-1]


class MockPaginatedRequestSettings(MockRequestSettings, PaginatedRequestSettings):
    @staticmethod
    def get_offset(url: StrOrURL) -> int:
        params = url.query if isinstance(url, URL) else parse_qs(urlparse(url).query)
        offset = params.get("offset", [0])
        return int(offset[0] if isinstance(offset, list) else offset)

    @staticmethod
    def get_limit(url: StrOrURL) -> int:
        params = url.query if isinstance(url, URL) else parse_qs(urlparse(url).query)
        limit = params.get("limit", 50)
        return int(limit[0] if isinstance(limit, list) else limit)
