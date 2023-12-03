from abc import ABCMeta
from typing import Any

from syncify.remote.api.core import RemoteAPICore
from syncify.remote.enums import RemoteItemType
from syncify.spotify.api import __URL_API__
from syncify.utils.helpers import limit_value


class SpotifyAPICore(RemoteAPICore, metaclass=ABCMeta):

    @property
    def api_url_base(self) -> str:
        return __URL_API__

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_self(self) -> dict[str, Any]:
        """``GET: /me`` - Get API response for information on current user"""
        return self.get(url=f"{self.api_url_base}/me", use_cache=True, log_pad=71)

    def query(self, query: str, kind: RemoteItemType, limit: int = 10, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        ``GET: /search`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The remote item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        if not query or len(query) > 150:  # query is too short or too long, skip
            return []

        url = f"{self.api_url_base}/search"
        params = {'q': query, "type": kind.name.casefold(), "limit": limit_value(limit)}
        r = self.get(url, params=params, use_cache=use_cache)

        if "error" in r:
            self.logger.error(f"{'ERROR':<7}: {url:<43} | Query: {query} | {r['error']}")
            return []

        return r[f"{kind.name.casefold()}s"]["items"]
