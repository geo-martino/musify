from abc import ABCMeta
from typing import MutableMapping, List, Any

from syncify.spotify import ItemType, __URL_API__
from syncify.spotify.api.utilities import Utilities


class Basic(Utilities, metaclass=ABCMeta):

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_self(self) -> MutableMapping[str, Any]:
        """``GET: /me`` - Get API response for information on current user"""
        return self.get(url=f'{__URL_API__}/me', use_cache=True, log_pad=71)

    def query(
            self, query: str, kind: ItemType, limit: int = 10, use_cache: bool = True
    ) -> List[MutableMapping[str, Any]]:
        """
        ``GET: /search`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The Spotify item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        url = f'{__URL_API__}/search'
        params = {'q': query, 'type': kind.name.lower(), 'limit': self._limit_value(limit)}
        r = self.get(url, params=params, use_cache=use_cache)

        if 'error' in r:
            self._logger.error(f"{'ERROR':<7}: {url:<43} | Query: {query} | {r['error']}")
            return []

        return r[f'{kind.name.lower()}s']['items']
