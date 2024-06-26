from typing import Any

import pytest

from musify.api.cache.backend import ResponseCache, SQLiteCache
from musify.api.cache.backend.base import ResponseRepository
from musify.libraries.remote.core.api import RemoteAPI
from musify.libraries.remote.core.enum import RemoteObjectType
from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.factory import SpotifyObjectFactory
from tests.libraries.remote.core.api import RemoteAPIFixtures
from tests.libraries.remote.spotify.api.mock import SpotifyMock
from tests.libraries.remote.spotify.api.utils import get_limit


class SpotifyAPIFixtures(RemoteAPIFixtures):

    @property
    def _class(self) -> type[RemoteAPI]:
        return SpotifyAPI

    @pytest.fixture(scope="class")
    def object_factory(self) -> SpotifyObjectFactory:
        """Yield the object factory for Spotify objects as a pytest.fixture."""
        return SpotifyObjectFactory()

    @pytest.fixture
    async def cache(self) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        async with SQLiteCache.connect_with_in_memory_db() as cache:
            yield cache

    @pytest.fixture
    async def repository(
            self, object_type: RemoteObjectType, response: dict[str, Any], api_cache: SpotifyAPI, cache: ResponseCache
    ) -> ResponseRepository:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        return cache.get_repository_from_url(response[self.url_key])

    @pytest.fixture
    async def api_cache(self, api: SpotifyAPI, cache: ResponseCache, api_mock: SpotifyMock) -> SpotifyAPI:
        """Yield an authorised :py:class:`SpotifyAPI` object with a :py:class:`ResponseCache` configured."""
        async with SpotifyAPI(
                cache=cache,
                token=api.handler.authoriser.token,
                test_args=api.handler.authoriser.test_args,
                test_expiry=api.handler.authoriser.test_expiry,
                test_condition=api.handler.authoriser.test_condition,
        ) as api:
            api_mock.reset()  # entering context calls '/me' endpoint, reset to avoid issues asserting request counts
            yield api

    @pytest.fixture
    def responses(self, _responses: dict[str, dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
        return {id_: response for id_, response in _responses.items() if key is None or response[key]["total"] > 3}

    def reduce_items(
            self, response: dict[str, Any], key: str, api: SpotifyAPI, api_mock: SpotifyMock, pages: int = 3
    ) -> int:
        """
        Some tests require the existing items in a given ``response``
        to be less than the total available items for that ``response``.
        This function reduces the existing items so that the given number of ``pages``
        will be called when the test runs.

        :return: The number of items expected in each page.
        """
        response_items = response[key]
        limit = get_limit(
            response_items["total"],
            max_limit=min(len(response_items[api.items_key]) // 3, api_mock.limit_max),
            pages=pages
        )
        assert len(response_items[api.items_key]) >= limit

        response_reduced = api_mock.format_items_block(
            url=response_items[self.url_key],
            items=response_items[api.items_key][:limit],
            limit=limit,
            total=response_items["total"]
        )

        # assert ranges are valid for test to work and test value generated correctly
        assert 0 < len(response_reduced[api.items_key]) <= limit
        assert response_reduced["total"] == response_items["total"]
        assert response_reduced["total"] > response_reduced["limit"]
        assert response_reduced["total"] > len(response_reduced[api.items_key])

        response[key] = response_reduced

        return limit
