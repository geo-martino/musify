import contextlib
from abc import ABC, abstractmethod
from random import choice, randrange
from typing import Any

import pytest
from aiohttp import ClientResponse, ClientSession

from musify.api.cache.backend.base import ResponseRepository, ResponseCache, RequestSettings
from musify.api.exception import CacheError
from tests.api.cache.backend.utils import MockRequestSettings, MockPaginatedRequestSettings
from tests.utils import random_str

REQUEST_SETTINGS = [
    MockRequestSettings,
    MockPaginatedRequestSettings,
]


class BaseResponseTester(ABC):
    """Base functionality for all test suites related to `api.cache` package."""

    @staticmethod
    @abstractmethod
    def generate_connection() -> Any:
        """Generates and yields a :py:class:`Connection` for this backend type."""
        raise NotImplementedError

    @pytest.fixture
    def connection(self) -> Any:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest_asyncio.fixture."""
        return self.generate_connection()

    @staticmethod
    @abstractmethod
    def generate_item(settings: RequestSettings) -> tuple[Any, Any]:
        """
        Randomly generates an item (key, value) appropriate for the given ``settings``
        that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def generate_response_from_item(
            cls, settings: RequestSettings, key: Any, value: Any, session: ClientSession = None
    ) -> ClientResponse:
        """
        Generates a :py:class:`ClientResponse` appropriate for the given ``settings``
        from the given ``key`` and ``value`` that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def generate_bad_response_from_item(
            cls, settings: RequestSettings, key: Any, value: Any, session: ClientSession = None
    ) -> ClientResponse:
        """
        Generates a bad :py:class:`ClientResponse` appropriate for the given ``settings``
        from the given ``key`` and ``value`` that can be persisted to the repository.
        """
        raise NotImplementedError


class ResponseRepositoryTester(BaseResponseTester, ABC):
    """Run generic tests for :py:class:`ResponseRepository` implementations."""

    # noinspection PyArgumentList
    @pytest.fixture(scope="class", params=REQUEST_SETTINGS)
    def settings(self, request) -> RequestSettings:
        """
        Yields the :py:class:`RequestSettings` to use when creating a new :py:class:`ResponseRepository`
        as a pytest.fixture.
        """
        cls: type[RequestSettings] = request.param
        return cls(name="test")

    @pytest.fixture(scope="class")
    def valid_items(self, settings: RequestSettings) -> dict:
        """Yields expected items to be found in the repository that have not expired as a pytest.fixture."""
        return dict(self.generate_item(settings) for _ in range(randrange(3, 6)))

    @pytest.fixture(scope="class")
    def invalid_items(self, settings: RequestSettings) -> dict:
        """Yields expected items to be found in the repository that have passed the expiry time as a pytest.fixture."""
        return dict(self.generate_item(settings) for _ in range(randrange(3, 6)))

    @pytest.fixture(scope="class")
    def items(self, valid_items: dict, invalid_items: dict) -> dict:
        """Yields all expected items to be found in the repository as a pytest.fixture."""
        return valid_items | invalid_items

    @abstractmethod
    async def repository(
            self, connection: Any, settings: RequestSettings, valid_items: dict, invalid_items: dict
    ) -> ResponseRepository:
        """
        Yields a valid :py:class:`ResponseRepository` to use throughout tests in this suite as a pytest_asyncio.fixture.
        Should produce a repository for each type of :py:class:`RequestSettings` type
        as given by the request fixture.
        """
        raise NotImplementedError

    @staticmethod
    async def test_close(repository: ResponseRepository):
        key, _ = await anext(aiter(repository))
        await repository.close()

        with pytest.raises(ValueError):
            await repository.get_response(key)

    @staticmethod
    async def test_count(repository: ResponseRepository, items: dict, valid_items: dict):
        assert await repository.count() == len(items)
        assert await repository.count(False) == len(valid_items)

    @abstractmethod
    def test_serialize(self, repository: ResponseRepository):
        raise NotImplementedError

    @abstractmethod
    def test_deserialize(self, repository: ResponseRepository):
        raise NotImplementedError

    def test_get_key_from_request(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        request = self.generate_response_from_item(repository.settings, key, value).request_info
        assert repository.get_key_from_request(request) == key

    def test_get_key_from_invalid_request(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        request = self.generate_bad_response_from_item(repository.settings, key, value).request_info
        assert repository.get_key_from_request(request) is None

    @staticmethod
    async def test_get_responses_from_keys(repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        assert await repository.get_response(key) == value
        assert await repository.get_responses(valid_items.keys()) == list(valid_items.values())

    async def test_get_response_on_missing(self, repository: ResponseRepository, valid_items: dict):
        key, value = self.generate_item(repository.settings)
        assert not await repository.contains(key)

        assert await repository.get_response(key) is None
        assert await repository.get_responses(list(valid_items) + [key]) == list(valid_items.values())

    async def test_get_responses_from_requests(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        request = self.generate_response_from_item(repository.settings, key, value).request_info
        assert await repository.get_response(request) == value

        requests = [
            self.generate_response_from_item(repository.settings, key, value).request_info
            for key, value in valid_items.items()
        ]
        assert await repository.get_responses(requests) == list(valid_items.values())

    async def test_get_response_from_responses(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = self.generate_response_from_item(repository.settings, key, value)
        assert await repository.get_response(response) == value

        responses = [
            self.generate_response_from_item(repository.settings, key, value) for key, value in valid_items.items()
        ]
        assert await repository.get_responses(responses) == list(valid_items.values())

    async def test_get_response_from_responses_on_missing(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = self.generate_bad_response_from_item(repository.settings, key, value)
        assert await repository.get_response(response) is None

        responses = [
            self.generate_bad_response_from_item(repository.settings, key, value) for key, value in valid_items.items()
        ]
        assert await repository.get_responses(responses) == []

    async def test_set_item_from_key_value_pair(self, repository: ResponseRepository):
        items = [self.generate_item(repository.settings) for _ in range(randrange(3, 6))]
        assert all([not await repository.contains(key) for key, _ in items])

        for key, value in items:
            await repository._set_item_from_key_value_pair(key, value)

        assert all([await repository.contains(key) for key, _ in items])
        for key, value in items:
            assert await repository.get_response(key) == value

    async def test_save_response(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        response = self.generate_response_from_item(repository.settings, key, value)
        assert not await repository.contains(key)

        await repository.save_response(response)
        assert repository.contains(key)
        assert await repository.get_response(key) == value

    async def test_save_response_fails_silently(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        assert not await repository.contains(key)

        response = self.generate_bad_response_from_item(repository.settings, key, value)
        await repository.save_response(response)
        assert not await repository.contains(key)

    async def test_save_responses(self, repository: ResponseRepository):
        items = dict(self.generate_item(repository.settings) for _ in range(randrange(3, 6)))
        responses = [self.generate_response_from_item(repository.settings, key, value) for key, value in items.items()]
        assert all([not await repository.contains(key) for key in items])

        await repository.save_responses(responses)
        assert all([await repository.contains(key) for key in items])
        for key, value in items.items():
            assert await repository.get_response(key) == value

    async def test_save_responses_fails_silently(self, repository: ResponseRepository):
        items = dict(self.generate_item(repository.settings) for _ in range(randrange(3, 6)))
        assert all([not await repository.contains(key) for key in items])

        responses = [
            self.generate_bad_response_from_item(repository.settings, key, value) for key, value in items.items()
        ]
        await repository.save_responses(responses)
        assert all([not await repository.contains(key) for key in items])

    async def test_delete_response_on_missing(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        assert not await repository.contains(key)
        assert not await repository.delete_response(key)

    @staticmethod
    async def test_delete_response_from_key(repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        assert await repository.contains(key)

        assert await repository.delete_response(key)
        assert not await repository.contains(key)

    async def test_delete_response_from_request(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        request = self.generate_response_from_item(repository.settings, key, value).request_info
        assert await repository.contains(key)

        assert await repository.delete_response(request)
        assert not await repository.contains(key)

    async def test_delete_responses_from_requests(self, repository: ResponseRepository, valid_items: dict):
        requests = [
            self.generate_response_from_item(repository.settings, key, value).request_info
            for key, value in valid_items.items()
        ]
        for key in valid_items:
            assert await repository.contains(key)

        assert await repository.delete_responses(requests) == len(requests)
        for key in valid_items:
            assert not await repository.contains(key)

    async def test_delete_response_from_response(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = self.generate_response_from_item(repository.settings, key, value)
        assert await repository.contains(key)

        assert await repository.delete_response(response)
        assert not await repository.contains(key)

    async def test_delete_responses_from_responses(self, repository: ResponseRepository, valid_items: dict):
        responses = [
            self.generate_response_from_item(repository.settings, key, value)
            for key, value in valid_items.items()
        ]
        for key in valid_items:
            assert await repository.contains(key)

        assert await repository.delete_responses(responses) == len(responses)
        for key in valid_items:
            assert not await repository.contains(key)


class ResponseCacheTester(BaseResponseTester, ABC):
    """Run generic tests for :py:class:`ResponseCache` implementations."""

    # noinspection PyArgumentList
    @staticmethod
    def generate_settings() -> RequestSettings:
        """Randomly generates a :py:class:`RequestSettings` object that can be used to create a repository."""
        cls: type[RequestSettings] = choice(REQUEST_SETTINGS)
        return cls(name=random_str(20, 30))

    @staticmethod
    @abstractmethod
    def generate_response(settings: RequestSettings, session: ClientSession = None) -> ClientResponse:
        """
        Randomly generates a :py:class:`ClientResponse` appropriate for the given ``settings``
        that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    @contextlib.asynccontextmanager
    async def generate_cache(cls, connection: Any) -> ResponseCache:
        """
        Generates a :py:class:`ResponseCache` for this backend type
        with many randomly generated :py:class:`ResponseRepository` objects assigned
        and a ``response_getter`` assigned to get these repositories.
        """
        raise NotImplementedError

    # noinspection PyTestUnpassedFixture
    @pytest.fixture
    async def cache(self, connection: Any) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        async with self.generate_cache(connection) as cache:
            yield cache

    @staticmethod
    @abstractmethod
    def get_repository_from_url(cache: ResponseCache, url: str) -> ResponseCache:
        """Returns a repository for the given ``url`` from the given ``cache``."""
        raise NotImplementedError

    @staticmethod
    async def test_close(cache: ResponseCache):
        key = choice(list(cache.values()))
        await cache.close()

        with pytest.raises(Exception):
            await cache.get_response(key)

    async def test_create_repository(self, cache: ResponseCache):
        settings = self.generate_settings()
        assert settings.name not in cache

        await cache.create_repository(settings)
        assert settings.name in cache
        assert cache[settings.name].settings == settings

        # does not create a repository that already exists
        repository = choice(list(cache.values()))
        with pytest.raises(CacheError):
            await cache.create_repository(repository.settings)

    def test_get_repository_for_url(self, cache: ResponseCache):
        repository = choice(list(cache.values()))
        url = self.generate_response(repository.settings).request_info.url

        assert cache.get_repository_from_url(url).settings.name == repository.settings.name
        assert cache.get_repository_from_url(f"http://www.does-not-exist.com/{random_str()}/{random_str()}") is None
        cache.repository_getter = None
        assert cache.get_repository_from_url(url) is None

    def test_get_repository_for_requests(self, cache: ResponseCache):
        repository = choice(list(cache.values()))
        requests = [self.generate_response(repository.settings).request_info for _ in range(3, 6)]
        cache.get_repository_from_requests(requests)

    def test_get_repository_for_responses(self, cache: ResponseCache):
        repository = choice(list(cache.values()))
        responses = [self.generate_response(repository.settings) for _ in range(3, 6)]
        assert cache.get_repository_from_requests(responses).settings.name == repository.settings.name

        new_settings = self.generate_settings()
        new_responses = [self.generate_response(new_settings) for _ in range(3, 6)]
        assert cache.get_repository_from_requests(new_responses) is None

        with pytest.raises(CacheError):  # multiple types given
            cache.get_repository_from_requests(responses + new_responses)

        cache.repository_getter = None
        assert cache.get_repository_from_requests(responses) is None

    async def test_repository_operations(self, cache: ResponseCache):
        repository = choice(list(cache.values()))

        response = self.generate_response(repository.settings)
        key = repository.get_key_from_request(response.request_info)
        await cache.save_response(response)
        assert await repository.contains(key)

        assert await cache.get_response(response) == repository.deserialize(await response.text())

        assert await cache.delete_response(response)
        assert not await repository.contains(key)
