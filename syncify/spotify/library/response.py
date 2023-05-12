from abc import ABCMeta, abstractmethod
from typing import Any, MutableMapping, Self, Optional

from spotify.api.utilities import APIMethodInputType
from syncify.spotify.api import API
from syncify.abstract import PrettyPrinter


class SpotifyResponse(PrettyPrinter, metaclass=ABCMeta):
    """
    Extracts key data from a Spotify API JSON response.

    :param response: The Spotify API JSON response
    """

    _list_sep = "; "
    _url_pad = 71

    api: API

    def __init__(self, response: MutableMapping[str, Any]):
        self.response = response
        self._check_type()

        self.id: Optional[str] = response["id"]
        self.uri: str = response["uri"]
        self.has_uri: bool = not response.get("is_local", False)

        self.url: Optional[str] = response["href"]
        self.url_ext: Optional[str] = response["external_urls"].get("spotify")

    def _check_type(self) -> None:
        """Checks the given response is compatible with this object type, raises an exception if not"""
        kind = self.__class__.__name__.lower().replace("spotify", "")
        if self.response.get("type") != kind:
            raise ValueError(f"Response is not of type '{kind}': {self.response.get('type')}")

    @classmethod
    def _check_for_api(cls):
        """Checks the API has been set on the class, raises an exception if not"""
        if cls.api is None:
            raise ValueError("API is not set. Assign an API to the SpotifyResponse class first.")

    @classmethod
    @abstractmethod
    def load(cls, value: APIMethodInputType, use_cache: bool = True) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        The given ``value`` may be:
            * A single string value representing a URL/URI/ID.
            * A list of string values representing a URLs/URIs/IDs of the same type.
            * A Spotify API JSON response for a collection with a valid ID value under an ``id`` key.
            * A list of Spotify API JSON responses for a collection with a valid ID value under an ``id`` key.

        When a list is given, only the first item is processed.

        :param value: The value representing some Spotify artist. See description for allowed value types.
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

    def replace(self, response: MutableMapping[str, Any]) -> None:
        """
        Replace the extracted metadata on this object by extracting data from the given response
        No API calls are made for this function.
        """
        self.__init__(response)

    def as_dict(self) -> MutableMapping[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "response"}
