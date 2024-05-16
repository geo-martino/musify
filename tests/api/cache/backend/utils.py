from urllib.parse import parse_qs, urlparse

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings


class MockRequestSettings(RequestSettings):

    def get_id(self, url: str) -> str:
        return urlparse(url).path.split("/")[-1]


class MockPaginatedRequestSettings(MockRequestSettings, PaginatedRequestSettings):
    def get_offset(self, url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("offset", [0])[0])

    def get_limit(self, url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("page_count", [0])[0])
