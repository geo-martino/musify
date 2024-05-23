import json
from typing import Any

import pytest
from aiohttp import ClientRequest
from yarl import URL

from musify.api.cache.response import CachedResponse


class TestCachedResponse:

    @pytest.fixture(scope="class")
    def http_request(self) -> ClientRequest:
        """Yields a basic :py:class:`ClientRequest` as a pytest.fixture."""
        return ClientRequest(
            method="GET", url=URL("https://www.test.com"), headers={"Content-Type": "application/json"}
        )

    @pytest.fixture(scope="class")
    def data(self) -> dict[str, Any]:
        """Yields the expected payload dict response for a given request as a pytest.fixture."""
        return {
            "1": "val1",
            "2": "val2",
            "3": "val3",
        }

    @pytest.fixture
    def http_response(self, http_request: ClientRequest, data: dict[str, Any]) -> CachedResponse:
        """Yields the expected response for a given request as a pytest.fixture."""
        return CachedResponse(request=http_request, data=json.dumps(data))

    async def test_read(self, http_response: CachedResponse, data: dict[str, Any]):
        assert await http_response.read() == json.dumps(data).encode()
        assert await http_response.text() == json.dumps(data)
        assert await http_response.json() == data
