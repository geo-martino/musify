from abc import ABC, abstractmethod
from random import choice, randrange
from typing import Any

import pytest
from requests import Response

from musify.api.cache.backend.base import ResponseRepository, Connection, ResponseCache, RequestSettings
from musify.api.exception import CacheError
from musify.exception import MusifyKeyError
from tests.api.cache.backend.utils import MockRequestSettings, MockPaginatedRequestSettings
from tests.utils import random_str

REQUEST_SETTINGS = [
    MockRequestSettings,
    MockPaginatedRequestSettings,
]


class ResponseRepositoryTester(ABC):

    @staticmethod
    @abstractmethod
    def generate_item(settings: RequestSettings) -> tuple[Any, Any]:
        """
        Randomly generates an item (key, value) appropriate for the given ``settings``
        that can be persisted to the repository.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def generate_response_from_item(settings: RequestSettings, key: Any, value: Any) -> Response:
        """
        Generates a :py:class:`Response` appropriate for the given ``settings`` from the given ``key`` and ``value``
        that can be persisted to the repository.
        """
        raise NotImplementedError

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

    @staticmethod
    @abstractmethod
    def connection() -> Connection:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest.fixture."""
        raise NotImplementedError

    @abstractmethod
    def repository(self, request, connection: Connection, valid_items: dict, invalid_items: dict) -> ResponseRepository:
        """
        Yields a valid :py:class:`ResponseRepository` to use throughout tests in this suite as a pytest.fixture.
        Should produce a repository for each type of :py:class:`RequestSettings` type
        as given by the request fixture.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def connection_closed_exception(self) -> type[Exception]:
        """Returns the exception class to expect when executing against a closed connection."""
        raise NotImplementedError

    def test_close(self, repository: ResponseRepository):
        key = next(iter(repository))
        repository.close()

        with pytest.raises(self.connection_closed_exception):
            repository.get_response(key)

    @staticmethod
    def test_count(repository: ResponseRepository, items: dict, valid_items: dict):
        assert len(repository) == len(items)
        assert repository.count() == len(items)
        assert repository.count(False) == len(valid_items)

    @abstractmethod
    def test_serialise(self, repository: ResponseRepository):
        raise NotImplementedError

    @abstractmethod
    def test_deserialise(self, repository: ResponseRepository):
        raise NotImplementedError

    def test_get_key_from_request(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        request = self.generate_response_from_item(repository.settings, key, value).request
        assert repository.get_key_from_request(request) == key

    def test_get_response_on_missing(self, repository: ResponseRepository, valid_items: dict):
        key, value = self.generate_item(repository.settings)
        assert key not in repository

        with pytest.raises(MusifyKeyError):
            assert repository[key]

        assert repository.get(key) is None
        assert repository.get_response(key) is None
        assert repository.get_responses(list(valid_items) + [key]) == list(valid_items.values())

    @staticmethod
    def test_get_response_from_key(repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))

        assert repository[key] == value
        assert repository.get(key) == value
        assert repository.get_response(key) == value

    @staticmethod
    def test_get_responses_from_keys(repository: ResponseRepository, valid_items: dict):
        assert repository.get_responses(valid_items.keys()) == list(valid_items.values())

    def test_get_response_from_request(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        request = self.generate_response_from_item(repository.settings, key, value).request
        assert repository.get_response(request) == value

    def test_get_responses_from_requests(self, repository: ResponseRepository, valid_items: dict):
        requests = [
            self.generate_response_from_item(repository.settings, key, value).request
            for key, value in valid_items.items()
        ]
        assert repository.get_responses(requests) == list(valid_items.values())

    def test_get_response_from_response(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = self.generate_response_from_item(repository.settings, key, value)
        assert repository.get_response(response) == value

    def test_get_responses_from_responses(self, repository: ResponseRepository, valid_items: dict):
        responses = [
            self.generate_response_from_item(repository.settings, key, value) for key, value in valid_items.items()
        ]
        assert repository.get_responses(responses) == list(valid_items.values())

    def test_save_response_from_key(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        assert key not in repository

        repository[key] = value
        assert key in repository
        assert repository[key] == value

    def test_save_responses_from_dict(self, repository: ResponseRepository):
        items = dict(self.generate_item(repository.settings) for _ in range(randrange(3, 6)))
        assert all(key not in repository for key in items)

        repository.update(items)
        assert all(key in repository for key in items)
        for key, value in items.items():
            assert repository[key] == value

    def test_save_response(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        response = self.generate_response_from_item(repository.settings, key, value)
        assert key not in repository

        repository.save_response(response)
        assert key in repository
        assert repository[key] == value

    def test_save_responses(self, repository: ResponseRepository):
        items = dict(self.generate_item(repository.settings) for _ in range(randrange(3, 6)))
        responses = [self.generate_response_from_item(repository.settings, key, value) for key, value in items.items()]
        assert all(key not in repository for key in items)

        repository.save_responses(responses)
        assert all(key in repository for key in items)
        for key, value in items.items():
            assert repository[key] == value

    def test_delete_response_on_missing(self, repository: ResponseRepository):
        key, value = self.generate_item(repository.settings)
        assert key not in repository

        with pytest.raises(MusifyKeyError):
            del repository[key]

        repository.delete_response(key)

    @staticmethod
    def test_delete_response_from_key(repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        assert key in repository

        del repository[key]
        assert key not in repository

    def test_delete_response_from_request(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        request = self.generate_response_from_item(repository.settings, key, value).request
        assert key in repository

        repository.delete_response(request)
        assert key not in repository

    def test_delete_responses_from_requests(self, repository: ResponseRepository, valid_items: dict):
        requests = [
            self.generate_response_from_item(repository.settings, key, value).request
            for key, value in valid_items.items()
        ]
        for key in valid_items:
            assert key in repository

        repository.delete_responses(requests)
        for key in valid_items:
            assert key not in repository

    def test_delete_response_from_response(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = self.generate_response_from_item(repository.settings, key, value)
        assert key in repository

        repository.delete_response(response)
        assert key not in repository

    def test_delete_responses_from_responses(self, repository: ResponseRepository, valid_items: dict):
        responses = [
            self.generate_response_from_item(repository.settings, key, value)
            for key, value in valid_items.items()
        ]
        for key in valid_items:
            assert key in repository

        repository.delete_responses(responses)
        for key in valid_items:
            assert key not in repository

    @staticmethod
    def test_mapping_functionality(repository: ResponseRepository, items: dict):
        key, value = choice(list(repository.items()))
        assert key in items
        assert items[key] == value

        repository.clear()
        assert key not in repository
        with pytest.raises(MusifyKeyError):
            assert repository[key]

        # TODO: add more here


class ResponseCacheTester:

    # noinspection PyArgumentList
    @staticmethod
    def generate_settings() -> RequestSettings:
        """Randomly generates a :py:class:`RequestSettings` object that can be used to create a repository."""
        cls: type[RequestSettings] = choice(REQUEST_SETTINGS)
        return cls(name=random_str(20, 30))

    @staticmethod
    @abstractmethod
    def generate_response(settings: RequestSettings) -> Response:
        """
        Randomly generates a :py:class:`Response` appropriate for the given ``settings``
        that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    def generate_cache(cls, connection: Connection) -> ResponseCache:
        """
        Generates a :py:class:`ResponseCache` for this backend type
        with many randomly generated :py:class:`ResponseRepository` objects assigned
        and a ``response_getter`` assigned to get these repositories.
        """
        raise NotImplementedError

    @abstractmethod
    def connection(self) -> Connection:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest.fixture."""
        raise NotImplementedError

    @pytest.fixture
    def cache(self, connection: Connection) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        return self.generate_cache(connection)

    @staticmethod
    @abstractmethod
    def get_repository_from_url(cache: ResponseCache, url: str) -> ResponseCache:
        """Returns a repository for the given ``url`` from the given ``cache``."""
        raise NotImplementedError

    @staticmethod
    def test_close(cache: ResponseCache):
        key = choice(list(cache.values()))
        cache.close()

        with pytest.raises(Exception):
            cache.get_response(key)

    def test_create_repository(self, cache: ResponseCache):
        settings = self.generate_settings()
        assert settings.name not in cache

        cache.create_repository(settings)
        assert settings.name in cache
        assert cache[settings.name].settings == settings

        # does not create a repository that already exists
        repository = choice(list(cache.values()))
        with pytest.raises(CacheError):
            cache.create_repository(repository.settings)

    @staticmethod
    def test_get_repository_for_url(cache: ResponseCache):
        name, repository = choice(list(cache.items()))
        url = f"http://www.test.com/{name}/{random_str()}"

        assert cache.get_repository_from_url(url).settings.name == repository.settings.name
        assert cache.get_repository_from_url(f"http://www.test.com/{random_str()}/{random_str()}") is None
        cache.repository_getter = None
        assert cache.get_repository_from_url(url) is None

    def test_get_repository_for_requests(self, cache: ResponseCache):
        name, repository = choice(list(cache.items()))
        requests = [self.generate_response(repository.settings).request for _ in range(3, 6)]
        cache._get_repository_from_requests(requests)

    def test_get_repository_for_responses(self, cache: ResponseCache):
        name, repository = choice(list(cache.items()))
        responses = [self.generate_response(repository.settings) for _ in range(3, 6)]
        for response in responses:
            print(response.url)
        assert cache._get_repository_from_requests(responses).settings.name == repository.settings.name

        new_settings = self.generate_settings()
        new_responses = [self.generate_response(new_settings) for _ in range(3, 6)]
        assert cache._get_repository_from_requests(new_responses) is None

        with pytest.raises(CacheError):  # multiple types given
            cache._get_repository_from_requests(responses + new_responses)

        cache.repository_getter = None
        assert cache._get_repository_from_requests(responses) is None

    @pytest.mark.skip(reason="Not yet implemented")
    def test_repository_operations(self, cache: ResponseCache):
        pass  # TODO
