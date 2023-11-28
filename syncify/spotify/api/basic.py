from abc import ABCMeta
from collections.abc import Mapping
from typing import Any

from syncify.spotify.api import __URL_API__
from syncify.spotify.api.request import RequestHandler
from syncify.spotify.enums import ItemType
from syncify.utils.helpers import limit_value
from syncify.utils.logger import Logger


class APIBase(RequestHandler, Logger):
    pass


class Basic(APIBase, metaclass=ABCMeta):

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_self(self) -> Mapping[str, Any]:
        """``GET: /me`` - Get API response for information on current user"""
        return self.get(url=f"{__URL_API__}/me", use_cache=True, log_pad=71)

    def query(
            self, query: str, kind: ItemType, limit: int = 10, use_cache: bool = True
    ) -> list[Mapping[str, Any]]:
        """
        ``GET: /search`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The Spotify item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        if not query or len(query) > 150:  # query is too short or too long, skip
            return []

        url = f"{__URL_API__}/search"
        params = {'q': query, "type": kind.name.casefold(), "limit": limit_value(limit)}
        r = self.get(url, params=params, use_cache=use_cache)

        if "error" in r:
            self.logger.error(f"{'ERROR':<7}: {url:<43} | Query: {query} | {r['error']}")
            return []

        return r[f"{kind.name.casefold()}s"]["items"]
