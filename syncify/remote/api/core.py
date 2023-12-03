from abc import ABCMeta, abstractmethod
from typing import Any

from syncify.remote.api.base import RemoteAPIBase
from syncify.remote.enums import RemoteItemType


class RemoteAPICore(RemoteAPIBase, metaclass=ABCMeta):

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    @abstractmethod
    def get_self(self) -> dict[str, Any]:
        """``GET`` - Get API response for information on current user"""
        raise NotImplementedError

    @abstractmethod
    def query(self, query: str, kind: RemoteItemType, limit: int = 10, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        ``GET`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The remote item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        raise NotImplementedError
