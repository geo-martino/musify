from abc import ABCMeta, abstractmethod
from typing import Any, Self

from syncify.abstract import Item, NamedObjectPrinter
from syncify.api.exception import APIError
from syncify.remote.api import RemoteAPI
from syncify.remote.base import Remote


class RemoteObject(NamedObjectPrinter, Remote, metaclass=ABCMeta):
    """
    Generic base class for remote objects. Extracts key data from a remote API JSON response.

    :param response: The remote API JSON response
    :param api: The instantiated and authorised API object for this source type.
    """

    __slots__ = ("response", "api")

    _url_pad = 71

    @property
    @abstractmethod
    def id(self) -> str:
        """The ID of this item/collection."""
        raise NotImplementedError

    @property
    @abstractmethod
    def uri(self) -> str:
        """The URI of this item/collection."""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_uri(self) -> bool:
        """Does this item/collection have a valid URI that is not a local URI."""
        raise NotImplementedError

    @property
    @abstractmethod
    def url(self) -> str:
        """The API URL of this item/collection."""
        raise NotImplementedError

    @property
    @abstractmethod
    def url_ext(self) -> str | None:
        """The external URL of this item/collection."""
        raise NotImplementedError

    def __init__(self, response: dict[str, Any], api: RemoteAPI | None = None):
        super().__init__()
        self.response = response
        self.api = api
        self._check_type()

    @abstractmethod
    def _check_type(self) -> None:
        """
        Checks the given response is compatible with this object type, raises an exception if not.

        :raise RemoteObjectTypeError: When the response type is not compatible with this object.
        """
        raise NotImplementedError

    def _check_for_api(self) -> None:
        """
        Checks the API has been set on the instance, raises an exception if not.

        :raise APIError: When the API has not been set for this instance.
        """
        if self.api is None:
            raise APIError("API is not set. Assign an API to this instance first.")

    @classmethod
    @abstractmethod
    def load(cls, value: str | dict[str, Any], api: RemoteAPI, use_cache: bool = True, *args, **kwargs) -> Self:
        """
        Generate a new object of this class,
        calling all required endpoints to get a complete set of data for this item type.

        ``value`` may be:
            * A string representing a URL/URI/ID.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.

        :param value: The value representing some remote object. See description for allowed value types.
        :param api: An authorised API object to load the object from.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError

    @abstractmethod
    def reload(self, use_cache: bool = True, *args, **kwargs) -> None:
        """
        Reload this object from the API, calling all required endpoints
        to get a complete set of data for this item type

        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError

    def as_dict(self):
        ignore = {"api", "response", "name", "remote_source", "unavailable_uri_dummy", "tag_sep", "clean_tags"}
        return {
            k: getattr(self, k) for k in self.__dir__()
            if not k.startswith("_")
            and k not in ignore
            and not callable(getattr(self, k))
            and k not in self.__annotations__
        }

    def __hash__(self):
        """Uniqueness of a remote object is its URI"""
        return hash(self.uri)


class RemoteItem(RemoteObject, Item, metaclass=ABCMeta):
    """Generic base class for remote items. Extracts key data from a remote API JSON response."""
    pass
