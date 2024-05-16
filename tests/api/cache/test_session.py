import sqlite3

import pytest

from musify.api.cache.backend.base import ResponseCache, Connection
from tests.api.cache.backend.test_sqlite import TestSQLiteCache
from tests.api.cache.backend.testers import ResponseCacheTester


class TestCachedSession:

    @pytest.fixture(scope="class", params=[
        (TestSQLiteCache, sqlite3.Connection(database="file::memory:"))
    ])
    def cache(self, request) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        tester: ResponseCacheTester = request.param[0]
        connection: Connection = request.param[1]
        return tester.generate_cache(connection=connection)

    def test_request(self, cache: ResponseCache):
        pass  # TODO
