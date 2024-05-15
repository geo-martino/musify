import logging
from abc import ABC, abstractmethod
from collections.abc import MutableMapping, Callable, Collection, Hashable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol, Self

from requests import Request, PreparedRequest, Response

from musify.api.exception import CacheError
from musify.log.logger import MusifyLogger


DEFAULT_EXPIRE: timedelta = timedelta(weeks=1)


class Connection(Protocol):

    def close(self) -> None:
        """Close the connection to the storage layer."""


@dataclass
class RequestSettings(ABC):
    """Settings for a request type for a given endpoint to be used to configure storage in the cache backend."""
    name: str

    @abstractmethod
    def get_id(self, url: str) -> str:
        """Extracts the ID for a request from the given ``url``."""
        raise NotImplementedError


class PaginatedRequestSettings(RequestSettings, ABC):
    @abstractmethod
    def get_offset(self, url: str) -> int:
        """Extracts the offset for a paginated request from the given ``url``."""
        raise NotImplementedError

    @abstractmethod
    def get_limit(self, url: str) -> int:
        """Extracts the limit for a paginated request from the given ``url``."""
        raise NotImplementedError


class ResponseRepository[T: Connection, KT, VT](MutableMapping[KT, VT], Hashable, ABC):

    __slots__ = ("logger", "connection", "settings", "_expire")

    @property
    def expire(self) -> datetime:
        """The datetime representing the maximum allowed expiry time from now."""
        return datetime.now() - self._expire

    def __init__(self, connection: T, settings: RequestSettings, expire: timedelta = DEFAULT_EXPIRE):
        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

        self.connection = connection
        self.settings = settings
        self._expire = expire

    def __hash__(self):
        return hash(self.settings.name)

    def close(self) -> None:
        """Close the connection to the storage layer."""
        self.commit()
        self.connection.close()

    @abstractmethod
    def commit(self) -> None:
        """Commit the changes to the data"""
        raise NotImplementedError

    @abstractmethod
    def count(self, expired: bool = True) -> int:
        """
        Get the number of responses in this storage.

        :param expired: Whether to include expired responses in the final count.
        :return: The number of responses in this storage.
        """
        raise NotImplementedError

    @abstractmethod
    def serialise(self, value: Any) -> VT:
        """Serialize a given ``value`` to a type that can be persisted to the storage layer."""
        raise NotImplementedError

    @abstractmethod
    def deserialise(self, value: VT) -> Any:
        """Deserialize a value from the storage layer to the expected response value type."""
        raise NotImplementedError

    @abstractmethod
    def get_key_from_request(self, request: Request | PreparedRequest) -> KT:
        """Extract the keys to use when persisting responses for a given ``request``"""
        raise NotImplementedError

    def get_response(self, request: KT | Request | PreparedRequest | Response) -> VT | None:
        """Get the response relating to the given ``request`` from this storage if it exists."""
        if isinstance(request, Response):
            request = request.request

        keys = self.get_key_from_request(request) if isinstance(request, Request | PreparedRequest) else request
        return self.get(keys, None)

    def get_responses(self, requests: Collection[KT | Request | PreparedRequest | Response]) -> list[VT]:
        """
        Get the responses relating to the given ``requests`` from this storage if they exist.
        Returns results unordered.
        """
        results = [self.get_response(request) for request in requests]
        return [result for result in results if result is not None]

    def save_response(self, response: Response) -> None:
        """Save the given ``response`` to this storage."""
        keys = self.get_key_from_request(response.request)
        self[keys] = response.text

    def save_responses(self, responses: Collection[Response]) -> None:
        """Save the given ``responses`` to this storage."""
        for response in responses:
            self.save_response(response)

    def delete_response(self, request: KT | Request | PreparedRequest | Response) -> None:
        """Delete the given ``request`` from this storage if it exists."""
        if isinstance(request, Response):
            request = request.request
        keys = self.get_key_from_request(request) if isinstance(request, Request | PreparedRequest) else request
        self.pop(keys, None)

    def delete_responses(self, requests: Collection[KT | Request | PreparedRequest | Response]) -> None:
        """Delete the given ``requests`` from this storage if they exist."""
        for request in requests:
            self.delete_response(request)


class ResponseCache[CT: Connection, ST: ResponseRepository](ABC):

    __slots__ = ("cache_name", "connection", "storage_getter", "expire", "storage")

    def __init__(
            self,
            cache_name: str,
            connection: CT,
            storage_getter: Callable[[Self, str], ST] = None,
            expire: timedelta = DEFAULT_EXPIRE,
    ):
        self.cache_name = cache_name
        self.connection = connection
        self.storage_getter = storage_getter
        self.expire = expire

        self.storage: dict[str, ST] = {}

    def close(self):
        """Close the connection to the storage layer."""
        self.connection.close()

    @abstractmethod
    def create_storage(self, settings: RequestSettings) -> ResponseRepository:
        """
        Create and return a :py:class:`SQLiteResponseStorage` and store this object in this cache.

        Creates a storage with the given ``settings`` in the cache if it doesn't exist.
        """
        raise NotImplementedError

    def get_storage_for_url(self, url: str) -> ST | None:
        """Returns the storage to use from the stored storages in this cache for the given URL."""
        if self.storage_getter is not None:
            return self.storage_getter(self, url)

    def _get_storage_for_requests(self, requests: Collection[Request | PreparedRequest | Response]) -> ST | None:
        storage = {
            self.get_storage_for_url(request.request.url if isinstance(request, Response) else request.url)
            for request in requests
        }
        if len(storage) > 1:
            raise CacheError(
                "Too many different types of requests given. Given requests must relate to the same storage type"
            )
        return next(iter(storage))

    def get_response(self, request: Request | PreparedRequest | Response) -> Any:
        """Get the response relating to the given ``request`` from the appropriate storage if it exists."""
        storage = self._get_storage_for_requests([request])
        if storage is not None:
            return storage.get_response(request)

    def get_responses(self, requests: Collection[Request | PreparedRequest | Response]) -> list:
        """
        Get the responses relating to the given ``requests`` from the appropriate storage if they exist.
        Returns results unordered.
        """
        storage = self._get_storage_for_requests(requests)
        if storage is not None:
            return storage.get_responses(requests)

    def save_response(self, response: Response) -> None:
        """Save the given ``response`` to the appropriate storage."""
        storage = self._get_storage_for_requests([response])
        if storage is not None:
            return storage.save_response(response)

    def save_responses(self, responses: Collection[Response]) -> None:
        """Save the given ``responses`` to the appropriate storage."""
        storage = self._get_storage_for_requests(responses)
        if storage is not None:
            return storage.save_responses(responses)

    def delete_response(self, request: Request | PreparedRequest | Response) -> None:
        """Delete the given ``request`` from the appropriate storage if it exists."""
        storage = self._get_storage_for_requests([request])
        if storage is not None:
            return storage.delete_response(request)

    def delete_responses(self, requests: Collection[Request | PreparedRequest | Response]) -> None:
        """Delete the given ``requests`` from the appropriate storage."""
        storage = self._get_storage_for_requests(requests)
        if storage is not None:
            return storage.delete_responses(requests)
