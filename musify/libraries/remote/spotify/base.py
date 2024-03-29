"""
Core abstract classes for the :py:mod:`Spotify` module.

These define the foundations of any Spotify object or item.
"""
from abc import ABCMeta
from typing import Any

from musify.libraries.remote.core.base import RemoteObject, RemoteItem
from musify.libraries.remote.core.enum import RemoteObjectType
from musify.libraries.remote.core.exception import RemoteObjectTypeError, RemoteError
from musify.libraries.remote.spotify.api import SpotifyAPI


class SpotifyObject(RemoteObject[SpotifyAPI], metaclass=ABCMeta):
    """Generic base class for Spotify-stored objects. Extracts key data from a Spotify API JSON response."""

    _url_pad = 71

    @property
    def id(self):
        return self.response["id"]

    @property
    def uri(self):
        return self.response["uri"]

    @property
    def has_uri(self):
        return not self.response.get("is_local", False)

    @property
    def url(self):
        return self.response["href"]

    @property
    def url_ext(self):
        return self.response["external_urls"].get("spotify")

    def __init__(self, response: dict[str, Any], api: SpotifyAPI | None = None, skip_checks: bool = False):
        super().__init__(response=response, api=api, skip_checks=skip_checks)

    def _check_type(self) -> None:
        """
        Checks the given response is compatible with this object type, raises an exception if not.

        :raise RemoteObjectTypeError: When the response type is not compatible with this object.
        """
        required_keys = {"id", "uri", "href", "external_urls"}
        for key in required_keys:
            if key not in self.response:
                raise RemoteError(f"Response does not contain all required keys: {required_keys}")

        kind = self.__class__.__name__.removeprefix("Spotify").lower()
        if self.response.get("type") != kind:
            kind = RemoteObjectType.from_name(kind)[0]
            raise RemoteObjectTypeError("Response type invalid", kind=kind, value=self.response.get("type"))


class SpotifyItem(SpotifyObject, RemoteItem, metaclass=ABCMeta):
    """Generic base class for Spotify-stored items. Extracts key data from a Spotify API JSON response."""
    pass
