"""
Base functionality to be shared by all classes that implement :py:class:`RemoteAPI` functionality for Spotify.
"""
from abc import ABC
from typing import Any

from yarl import URL

from musify.libraries.remote.core.api import RemoteAPI
from musify.libraries.remote.core.enum import RemoteObjectType


class SpotifyAPIBase(RemoteAPI, ABC):
    """Base functionality required for all endpoint functions for the Spotify API"""

    __slots__ = ()

    #: The key to reference when extracting items from a collection
    items_key = "items"

    @staticmethod
    def _get_key(key: str | RemoteObjectType | None) -> str | None:
        if key is None:
            return
        if isinstance(key, RemoteObjectType):
            key = key.name
        return key.lower().rstrip("s") + "s"

    @staticmethod
    def format_next_url(url: str | URL, offset: int = 0, limit: int = 20) -> str:
        """Format a `next` style URL for looping through API pages"""
        url = URL(url)

        params: dict[str, Any] = dict(url.query)
        params["offset"] = offset
        params["limit"] = limit

        url = url.with_query(params)
        return str(url)
