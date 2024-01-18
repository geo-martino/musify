"""
Base functionality to be shared by all classes that implement :py:class:`RemoteAPI` functionality for Spotify.
"""

from abc import ABCMeta
from typing import Any
from urllib.parse import parse_qs, urlparse, urlencode, quote, urlunparse

from musify.shared.remote.api import RemoteAPI
from musify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyAPIBase(RemoteAPI, SpotifyDataWrangler, metaclass=ABCMeta):
    """Base functionality required for all endpoint functions for the Spotify API"""

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
