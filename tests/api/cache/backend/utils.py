from typing import Any

from yarl import URL

from musify.api.cache.backend.base import RequestSettings


class MockRequestSettings(RequestSettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return "id",

    def get_key(self, url: str | URL, *_, **__) -> tuple[str | None, ...]:
        if str(url).endswith(".com"):
            return (None,)
        return URL(url).path.split("/")[-1] or None,

    @staticmethod
    def get_name(response: dict[str, Any]) -> str | None:
        return response.get("name")


class MockPaginatedRequestSettings(MockRequestSettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return *super().fields, "offset", "size"

    def get_key(self, url: str | URL, *_, **__) -> tuple[str | int | None, ...]:
        base = super().get_key(url=url)
        return *base, self.get_offset(url), self.get_limit(url)

    @staticmethod
    def get_offset(url: str | URL) -> int:
        params = URL(url).query
        return int(params.get("offset", 0))

    @staticmethod
    def get_limit(url: str | URL) -> int:
        params = URL(url).query
        return int(params.get("limit", 0))
