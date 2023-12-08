from abc import ABCMeta, abstractmethod
from typing import Any

from syncify.remote.api import APIMethodInputType
from syncify.remote.api.base import RemoteAPIBase
from syncify.remote.enums import RemoteItemType


class RemoteAPIItems(RemoteAPIBase, metaclass=ABCMeta):
    """API endpoints for processing all remote item types"""

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    @abstractmethod
    def get_items(
            self,
            values: APIMethodInputType,
            kind: RemoteItemType | None = None,
            limit: int = 50,
            use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        ``GET`` - Get information for given list of ``values``. Items may be:
            - A string representing a URL/URI/ID.
            - A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            - A remote API JSON response for a collection including some items under an ``items`` key,
            a valid ID value under an ``id`` key,
                and a valid item type value under a ``type`` key if ``kind`` is None.
            - A MutableSequence of remote API JSON responses for a collection including:
                - some items under an ``items`` key
                - a valid ID value under an ``id`` key
                - a valid item type value under a ``type`` key if ``kind`` is None.

        If a JSON response is given, this replaces the ``items`` with the new results.

        :param values: The values representing some remote items. See description for allowed value types.
            These items must all be of the same type of item i.e. all tracks OR all artists etc.
        :param kind: Item type if given string is ID.
        :param limit: Size of batches to request.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item.
        :raise RemoteItemTypeError: Raised when the function cannot determine the item type
            of the input ``values``. Or when it does not recognise the type of the input ``values`` parameter.
        """
        raise NotImplementedError

    @abstractmethod
    def get_tracks(
            self, values: APIMethodInputType, limit: int = 50, use_cache: bool = True, *args, **kwargs,
    ) -> list[dict[str, Any]]:
        """
        ``GET`` + GET: /audio-features`` and/or ``GET: /audio-analysis``

        Get audio features/analysis for list of tracks.
        Mostly just a wrapper for ``get_items`` and ``get_tracks`` functions.
        Items may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including some items under an ``items`` key
                and a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a collection including :
                - some items under an ``items`` key
                - a valid ID value under an ``id`` key.

        If a JSON response is given, this updates ``items`` by adding the results
        under the ``audio_features`` and ``audio_analysis`` keys as appropriate.

        :param values: The values representing some remote tracks. See description for allowed value types.
        :param limit: Size of batches to request when getting audio features.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: API JSON responses for each item.
        :raise RemoteItemTypeError: Raised when the item types of the input ``tracks``
            are not all tracks or IDs.
        """
        raise NotImplementedError
