from abc import ABCMeta

from syncify.spotify import ItemType, __URL_API__
from syncify.spotify.endpoints.utilities import Utilities


class Basic(Utilities, metaclass=ABCMeta):

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_self(self) -> dict:
        """``GET: /me`` - Get API response for information on current user"""
        return self.requests.get(url=f'{__URL_API__}/me', use_cache=True)

    def query(self, query: str, kind: ItemType, limit: int = 10, use_cache: bool = True) -> list:
        """
        ``GET: /search`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The Spotify item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        url = f'{__URL_API__}/search'
        params = {'q': query, 'type': kind.name.lower(), 'limit': self.limit_value(limit)}
        self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}} | Params: {params}")

        r = self.requests.get(url, params=params, use_cache=use_cache)
        if 'error' in r:
            self._logger.error(f"{'ERROR':<7}: {url:<{self.url_log_width}} | Query: {query} | {r['error']}")
            return []
        return r[f'{kind.name.lower()}s']['items']
