"""
Base functionality to be shared by all classes that implement :py:class:`RemoteAPI` functionality for Spotify.
"""
from abc import ABC
from typing import Any
from urllib.parse import parse_qs, urlparse, urlencode, quote, urlunparse

from musify.libraries.remote.core.api import RemoteAPI


class SpotifyAPIBase(RemoteAPI, ABC):
    """Base functionality required for all endpoint functions for the Spotify API"""

    __slots__ = ()

    #: The key to reference when extracting items from a collection
    items_key = "items"

    @staticmethod
    def format_next_url(url: str, offset: int = 0, limit: int = 20) -> str:
        """Format a `next` style URL for looping through API pages"""
        url_parsed = urlparse(url)
        params: dict[str, Any] = parse_qs(url_parsed.query)
        params["offset"] = offset
        params["limit"] = limit

        url_parts = list(url_parsed[:])
        url_parts[4] = urlencode(params, doseq=True, quote_via=quote)
        return str(urlunparse(url_parts))
