from random import choice
from typing import Any

import pytest
from aioresponses import aioresponses

from musify.api.cache.backend.base import ResponseCache
from musify.api.cache.session import CachedSession
from tests.api.cache.backend.test_sqlite import TestSQLiteCache as SQLiteCacheTester
from tests.api.cache.backend.testers import ResponseCacheTester
from tests.api.cache.backend.utils import MockRequestSettings
from tests.utils import random_str


class TestCachedSession:

    @pytest.fixture(scope="class", params=[SQLiteCacheTester])
    def tester(self, request) -> ResponseCacheTester:
        return request.param

    @pytest.fixture
    def connection(self, tester: ResponseCacheTester) -> Any:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest.fixture."""
        return tester.generate_connection()

    # noinspection PyTestUnpassedFixture
    @pytest.fixture
    async def cache(self, tester: ResponseCacheTester) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        async with tester.generate_cache() as cache:
            yield cache

    @pytest.fixture
    async def session(self, cache: ResponseCache) -> CachedSession:
        """
        Yields a valid :py:class:`CachedSession` with the given ``cache``
        to use throughout tests in this suite as a pytest.fixture.
        """
        async with CachedSession(cache=cache) as session:
            yield session

    async def test_context_management(self, cache: ResponseCache):
        # does not create repository backend resource until entered
        settings = MockRequestSettings(name=random_str(20, 30))
        session = CachedSession(cache=cache)
        repository = cache.create_repository(settings)

        with pytest.raises(Exception):
            await repository.count()
        async with session:
            await repository.count()

    async def test_request_cached(
            self,
            session: CachedSession,
            cache: ResponseCache,
            tester: ResponseCacheTester,
            requests_mock: aioresponses
    ):
        repository = choice(list(cache.values()))

        key, value = choice([(k, v) async for k, v in repository])
        assert await repository.contains(key)

        expected = tester.generate_response_from_item(repository.settings, key, value, session=session)
        request = expected.request_info
        headers = {"Content-Type": "application/json"}

        async with session.request(method=request.method, url=request.url, headers=headers) as response:
            assert await response.json() == await expected.json()
        requests_mock.assert_not_called()

    async def test_request_not_cached(
            self,
            session: CachedSession,
            cache: ResponseCache,
            tester: ResponseCacheTester,
            requests_mock: aioresponses,
    ):
        repository = choice(list(cache.values()))

        expected = tester.generate_response(repository.settings, session=session)
        request = expected.request_info
        headers = {"Content-Type": "application/json"}

        key = repository.get_key_from_request(request)
        assert not await repository.contains(key)

        requests_mock.get(request.url, body=await expected.text(), repeat=True)

        async with session.request(method=request.method, url=request.url, headers=headers, persist=False) as response:
            assert await response.json() == await expected.json()
        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 1
        assert not await repository.contains(key)

        async with session.request(method=request.method, url=request.url, headers=headers, persist=True) as response:
            assert await response.text() == await expected.text()
        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 2
        assert await repository.contains(key)

        async with session.request(method=request.method, url=request.url, headers=headers) as response:
            assert await response.json() == await expected.json()
        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 2
