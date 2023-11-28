from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from typing import Any, Self

from syncify.abstract.misc import PrettyPrinter
from syncify.spotify.enums import ItemType
from syncify.spotify.exception import APIError, SpotifyItemTypeError
from syncify.spotify.api import APIMethodInputType
from syncify.spotify.api.api import API


class SpotifyObject(PrettyPrinter, metaclass=ABCMeta):
    """
    Generic base class for Spotify-stored objects. Extracts key data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    _url_pad = 71

    api: API

    @property
    def id(self) -> str:
        """The ID of this item/collection."""
        return self.response["id"]

    @property
    def uri(self) -> str:
        """The URI of this item/collection."""
        return self.response["uri"]

    @property
    def has_uri(self) -> bool:
        """Does this item/collection have a valid URI that is not a local URI."""
        return not self.response.get("is_local", False)

    @property
    def url(self) -> str:
        """The API URL of this item/collection."""
        return self.response["href"]

    @property
    def url_ext(self) -> str | None:
        """The external URL of this item/collection."""
        return self.response["external_urls"].get("spotify")

    def __init__(self, response: MutableMapping[str, Any]):
        self.response = response
        self._check_type()

    def _check_type(self):
        """
        Checks the given response is compatible with this object type, raises an exception if not.

        :raises SpotifyItemTypeError: When the response type is not compatible with this object.
        """
        kind = self.__class__.__name__.casefold().replace("spotify", "")
        if self.response.get("type") != kind:
            kind = ItemType.from_name(kind)
            raise SpotifyItemTypeError(f"Response type invalid", kind=kind, value=self.response.get("type"))

    @classmethod
    def _check_for_api(cls):
        """
        Checks the API has been set on the class, raises an exception if not.

        :raises APIError: When the API has not been set for this class.
        """
        if cls.api is None:
            raise APIError("API is not set. Assign an API to the SpotifyResponse class first.")

    @classmethod
    @abstractmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        The given ``value`` may be:
            * A string representing a URL/URI/ID.
            * A collection of strings representing URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection with a valid ID value under an ``id`` key.
            * A list of Spotify API JSON responses for a collection with a valid ID value under an ``id`` key.

        When a list is given, only the first item is processed.

        :param value: The value representing some Spotify artist. See description for allowed value types.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError

    @abstractmethod
    def reload(self, use_cache: bool = True):
        """
        Reload this object from the API, calling all required endpoints
        to get a complete set of data for this item type

        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError

    def replace(self, response: MutableMapping[str, Any]):
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
            and k not in SpotifyObject.__annotations__
        }
