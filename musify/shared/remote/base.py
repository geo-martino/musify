"""
Core abstract classes for the :py:mod:`Remote` module.

These define the foundations of any remote object or item.
"""

from abc import ABCMeta, abstractmethod
from typing import Any, Self

from musify.shared.api.exception import APIError
from musify.shared.core.base import AttributePrinter, NameableTaggableMixin, Item
from musify.shared.remote import Remote
from musify.shared.remote.api import RemoteAPI


class RemoteObject(AttributePrinter, NameableTaggableMixin, Remote, metaclass=ABCMeta):
    """
    Generic base class for remote objects. Extracts key data from a remote API JSON response.

    :param response: The remote API JSON response
    :param api: The instantiated and authorised API object for this source type.
    """

    __slots__ = ("_response", "api")
    __attributes_ignore__ = ("api", "response")

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

    @property
    def response(self) -> dict[str, Any]:
        """The API response for this object"""
        return self._response

    def __init__(self, response: dict[str, Any], api: RemoteAPI | None = None, skip_checks: bool = False):
        super().__init__()
        self._response = response

        #: The :py:class:`RemoteAPI` to call when reloading
        self.api = api

        self._check_type()
        self.refresh(skip_checks=skip_checks)

    @abstractmethod
    def refresh(self, skip_checks: bool = False) -> None:
        """
        Refresh this object by updating from the stored API response.
        Useful for updating stored variables after making changes to the stored API response manually.
        """
        raise NotImplementedError

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

    def __hash__(self):
        """Uniqueness of a remote object is its URI"""
        return hash(self.uri)


class RemoteItem(RemoteObject, Item, metaclass=ABCMeta):
    """Generic base class for remote items. Extracts key data from a remote API JSON response."""

    __attributes_classes__ = (RemoteObject, Item)
