import sqlite3

import pytest

from musify.api.cache.backend.base import ResponseCache
from musify.api.cache.backend.sqlite import SQLiteCache


class TestCachedSession:

    @pytest.fixture(scope="class", params=[
        SQLiteCache(cache_name="test", connection=sqlite3.Connection(database="file::memory:?cache=shared"))
    ])
    def cache(self, request) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""

        def get_repository_for_url(cache: ResponseCache, url: str) -> ResponseCache:
            """Returns a repository for the given ``url`` from the given ``cache``."""
            pass  # TODO

        response_cache: ResponseCache = request.param

        # TODO: set up repositories on cache

        response_cache.repository_getter = get_repository_for_url
        return response_cache

    @pytest.mark.skip(reason="Not yet implemented")
    def test_request(self, cache: ResponseCache):
        pass  # TODO
