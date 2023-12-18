from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from typing import Any, Self

from syncify.remote.api import RemoteAPI
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.remote.types import APIMethodInputType
from syncify.remote.base import Remote
from syncify.abstract.item import BaseObject, Item
from syncify.abstract.misc import PrettyPrinter
from syncify.api.exception import APIError


class RemoteObjectMixin(Remote, BaseObject, metaclass=ABCMeta):
    pass


class RemoteObject(RemoteObjectMixin, PrettyPrinter, metaclass=ABCMeta):
    """
    Generic base class for remote objects. Extracts key data from a remote API JSON response.

    :ivar api: The instantiated and authorised API object for this source type.

    :param response: The remote API JSON response
    """

    _url_pad = 71
    api: RemoteAPI

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

    def __init__(self, response: MutableMapping[str, Any]):
        super().__init__()
        self.response = response
        self._check_type()

    @abstractmethod
    def _check_type(self) -> None:
        """
        Checks the given response is compatible with this object type, raises an exception if not.

        :raise RemoteObjectTypeError: When the response type is not compatible with this object.
        """
        raise NotImplementedError

    @classmethod
    def _check_for_api(cls) -> None:
        """
        Checks the API has been set on the class, raises an exception if not.

        :raise APIError: When the API has not been set for this class.
        """
        if cls.api is None:
            raise APIError("API is not set. Assign an API to this class first.")

    @classmethod
    @abstractmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True, *args, **kwargs) -> Self:
        """
        Generate a new object of this class,
        calling all required endpoints to get a complete set of data for this item type.

        The given ``value`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a collection with
                a valid ID value under an ``id`` key.

        When a list is given, only the first item is processed.

        :param value: The value representing some remote artist. See description for allowed value types.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError

    @abstractmethod
    def reload(self, use_cache: bool = True) -> None:
        """
        Reload this object from the API, calling all required endpoints
        to get a complete set of data for this item type

        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError

    def refresh(self, use_cache: bool = True) -> None:
        """
        Quickly refresh this item, calling the stored ``url`` and extracting metadata from the response

        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        self.__init__(self.api.get(url=self.url, use_cache=use_cache, log_pad=self._url_pad))

    def replace(self, response: MutableMapping[str, Any]) -> None:
        """
        Replace the extracted metadata on this object by extracting data from the given response
        No API calls are made for this function.
        """
        self.__init__(response)

    def as_dict(self):
        return {
            k: getattr(self, k) for k in self.__dir__()
            if not k.startswith("_")
            and k not in ["response", "name"]
            and not callable(getattr(self, k))
            and k not in self.__annotations__
        }


class RemoteObjectWranglerMixin[T: RemoteObject](RemoteDataWrangler, RemoteObject, metaclass=ABCMeta):
    pass


class RemoteItem(RemoteObject, Item, metaclass=ABCMeta):
    """Generic base class for remote items. Extracts key data from a remote API JSON response."""
    pass


class RemoteItemWranglerMixin[T: RemoteObject](RemoteDataWrangler, RemoteItem, metaclass=ABCMeta):
    pass
