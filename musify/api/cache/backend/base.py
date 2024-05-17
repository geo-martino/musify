import logging
from abc import ABC, abstractmethod
from collections.abc import MutableMapping, Callable, Collection, Hashable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol, Self

from dateutil.relativedelta import relativedelta
from requests import Request, PreparedRequest, Response

from musify.api.exception import CacheError
from musify.log.logger import MusifyLogger
from musify.types import UnitCollection
from musify.utils import to_collection

DEFAULT_EXPIRE: timedelta = timedelta(weeks=1)


class Connection(Protocol):
    """The expected protocol for a backend connection"""

    def close(self) -> None:
        """Close the connection to the repository."""


@dataclass
class RequestSettings(ABC):
    """Settings for a request type for a given endpoint to be used to configure a repository in the cache backend."""
    #: That name of the repository in the backend
    name: str

    @abstractmethod
    def get_id(self, url: str) -> str:
        """Extracts the ID for a request from the given ``url``."""
        raise NotImplementedError


class PaginatedRequestSettings(RequestSettings, ABC):
    """
    Settings for a request type for a given endpoint which returns a paginated response
    to be used to configure a repository in the cache backend.
    """

    @abstractmethod
    def get_offset(self, url: str) -> int:
        """Extracts the offset for a paginated request from the given ``url``."""
        raise NotImplementedError

    @abstractmethod
    def get_limit(self, url: str) -> int:
        """Extracts the limit for a paginated request from the given ``url``."""
        raise NotImplementedError


class ResponseRepository[T: Connection, KT, VT](MutableMapping[KT, VT], Hashable, ABC):
    """
    Represents a repository in the backend cache, providing a dict-like interface
    for interacting with this repository.

    A repository is a data store within the backend e.g. a table in a database.

    :param connection: The connection to the backend cache.
    :param settings: The settings to use to identify and interact with the repository in the backend.
    :param expire: The expiry time to apply to cached responses after which responses are invalidated.
    """

    __slots__ = ("logger", "connection", "settings", "_expire")

    @property
    def expire(self) -> datetime:
        """The datetime representing the maximum allowed expiry time from now."""
        return datetime.now() + self._expire

    def __init__(self, connection: T, settings: RequestSettings, expire: timedelta | relativedelta = DEFAULT_EXPIRE):
        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

        self.connection = connection
        self.settings = settings
        self._expire = expire

    def __hash__(self):
        return hash(self.settings.name)

    def close(self) -> None:
        """Close the connection to the repository."""
        self.commit()
        self.connection.close()

    @abstractmethod
    def commit(self) -> None:
        """Commit the changes to the data"""
        raise NotImplementedError

    @abstractmethod
    def count(self, expired: bool = True) -> int:
        """
        Get the number of responses in this repository.

        :param expired: Whether to include expired responses in the final count.
        :return: The number of responses in this repository.
        """
        raise NotImplementedError

    @abstractmethod
    def serialize(self, value: Any) -> VT:
        """Serialize a given ``value`` to a type that can be persisted to the repository."""
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, value: VT) -> Any:
        """Deserialize a value from the repository to the expected response value type."""
        raise NotImplementedError

    @abstractmethod
    def get_key_from_request(self, request: Request | PreparedRequest | Response) -> KT:
        """Extract the keys to use when persisting responses for a given ``request``"""
        raise NotImplementedError

    def get_response(self, request: KT | Request | PreparedRequest | Response) -> VT | None:
        """Get the response relating to the given ``request`` from this repository if it exists."""
        if isinstance(request, Request | PreparedRequest | Response):
            request = self.get_key_from_request(request)
        return self.get(request, None)

    def get_responses(self, requests: Collection[KT | Request | PreparedRequest | Response]) -> list[VT]:
        """
        Get the responses relating to the given ``requests`` from this repository if they exist.
        Returns results unordered.
        """
        results = [self.get_response(request) for request in requests]
        return [result for result in results if result is not None]

    def save_response(self, response: Response) -> None:
        """Save the given ``response`` to this repository."""
        keys = self.get_key_from_request(response)
        self[keys] = response.text

    def save_responses(self, responses: Collection[Response]) -> None:
        """Save the given ``responses`` to this repository."""
        for response in responses:
            self.save_response(response)

    def delete_response(self, request: KT | Request | PreparedRequest | Response) -> None:
        """Delete the given ``request`` from this repository if it exists."""
        if isinstance(request, Request | PreparedRequest | Response):
            request = self.get_key_from_request(request)
        self.pop(request, None)

    def delete_responses(self, requests: Collection[KT | Request | PreparedRequest | Response]) -> None:
        """Delete the given ``requests`` from this repository if they exist."""
        for request in requests:
            self.delete_response(request)


class ResponseCache[CT: Connection, ST: ResponseRepository](MutableMapping[str, ST], ABC):
    """
    Represents a backend cache of many repositories, providing a dict-like interface for interacting with them.

    :param cache_name: The name to give to this cache.
    :param connection: The connection to the backend cache.
    :param repository_getter: A function that can be used to identify the repository in this cache
        that matches a given URL.
    :param expire: The expiry time to apply to cached responses after which responses are invalidated.
    """

    __slots__ = ("cache_name", "connection", "repository_getter", "expire", "_repositories")

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    @abstractmethod
    def type(cls) -> str:
        """A string representing the type of the backend this class represents."""
        # raise NotImplementedError - omitted here as it causes docs build to fail

    @classmethod
    @abstractmethod
    def connect(cls, value: Any, **kwargs) -> Self:
        """Connect to the backend from a given generic ``value``."""
        raise NotImplementedError

    def __init__(
            self,
            cache_name: str,
            connection: CT,
            repository_getter: Callable[[Self, str], ST] = None,
            expire: timedelta | relativedelta = DEFAULT_EXPIRE,
    ):
        super().__init__()

        self.cache_name = cache_name
        self.connection = connection
        self.repository_getter = repository_getter
        self.expire = expire

        self._repositories: dict[str, ST] = {}

    def __repr__(self):
        return repr(self._repositories)

    def __str__(self):
        return str(self._repositories)

    def __iter__(self):
        return iter(self._repositories)

    def __len__(self):
        return len(self._repositories)

    def __getitem__(self, item):
        return self._repositories[item]

    def __setitem__(self, key, value):
        self._repositories[key] = value

    def __delitem__(self, key):
        del self._repositories[key]

    def close(self):
        """Close the connection to the repository."""
        self.connection.close()

    @abstractmethod
    def create_repository(self, settings: RequestSettings) -> ResponseRepository:
        """
        Create and return a :py:class:`SQLiteResponseStorage` and store this object in this cache.

        Creates a repository with the given ``settings`` in the cache if it doesn't exist.
        """
        raise NotImplementedError

    def get_repository_from_url(self, url: str) -> ST | None:
        """Returns the repository to use from the stored repositories in this cache for the given ``url``."""
        if self.repository_getter is not None:
            return self.repository_getter(self, url)

    def get_repository_from_requests(self, requests: UnitCollection[Request | PreparedRequest | Response]) -> ST | None:
        """Returns the repository to use from the stored repositories in this cache for the given ``requests``."""
        requests = to_collection(requests)
        results = {self.get_repository_from_url(request.url) for request in requests}
        if len(results) > 1:
            raise CacheError(
                "Too many different types of requests given. Given requests must relate to the same repository type"
            )
        return next(iter(results))

    def get_response(self, request: Request | PreparedRequest | Response) -> Any:
        """Get the response relating to the given ``request`` from the appropriate repository if it exists."""
        repository = self.get_repository_from_requests([request])
        if repository is not None:
            return repository.get_response(request)

    def get_responses(self, requests: Collection[Request | PreparedRequest | Response]) -> list:
        """
        Get the responses relating to the given ``requests`` from the appropriate repository if they exist.
        Returns results unordered.
        """
        repository = self.get_repository_from_requests(requests)
        if repository is not None:
            return repository.get_responses(requests)

    def save_response(self, response: Response) -> None:
        """Save the given ``response`` to the appropriate repository."""
        repository = self.get_repository_from_requests([response])
        if repository is not None:
            return repository.save_response(response)

    def save_responses(self, responses: Collection[Response]) -> None:
        """Save the given ``responses`` to the appropriate repository."""
        repository = self.get_repository_from_requests(responses)
        if repository is not None:
            return repository.save_responses(responses)

    def delete_response(self, request: Request | PreparedRequest | Response) -> None:
        """Delete the given ``request`` from the appropriate repository if it exists."""
        repository = self.get_repository_from_requests([request])
        if repository is not None:
            return repository.delete_response(request)

    def delete_responses(self, requests: Collection[Request | PreparedRequest | Response]) -> None:
        """Delete the given ``requests`` from the appropriate repository."""
        repository = self.get_repository_from_requests(requests)
        if repository is not None:
            return repository.delete_responses(requests)
