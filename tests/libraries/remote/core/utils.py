import re
from abc import abstractmethod
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs

from requests_mock import Mocker
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy

from musify.libraries.remote.core.enum import RemoteIDType, RemoteObjectType

ALL_ID_TYPES = RemoteIDType.all()
ALL_ITEM_TYPES = RemoteObjectType.all()


class RemoteMock(Mocker):
    """Generates responses and sets up Remote API requests mock"""

    range_start = 25
    range_stop = 50
    range_max = 200

    limit_lower = 10
    limit_upper = 20
    limit_max = 50

    @property
    @abstractmethod
    def item_type_map(self) -> dict[RemoteObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`RemoteObjectType` to the mocked items mapped as ``{<ID>: <item>}``"""
        raise NotImplementedError

    @property
    @abstractmethod
    def item_type_map_user(self) -> dict[RemoteObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`RemoteObjectType` to the mocked user items mapped as ``{<ID>: <item>}``"""
        raise NotImplementedError

    @staticmethod
    def calculate_pages(limit: int, total: int) -> int:
        """
        Calculates the numbers of a pages that need to be called from a given ``total`` and ``limit`` per page
        to get all items related to this response.
        """
        if limit > 0 and total > 0:
            return total // limit + (total % limit > 0)  # round up
        return 0

    @abstractmethod
    def calculate_pages_from_response(self, response: Mapping[str, Any]) -> int:
        """
        Calculates the numbers of a pages that need to be called for a given ``response``
        to get all items related to this response.
        """
        raise NotImplementedError

    def get_requests(
            self,
            url: str | re.Pattern[str] | None = None,
            method: str | None = None,
            params: dict[str, Any] | None = None,
            response: dict[str, Any] | None = None
    ) -> list[_RequestObjectProxy]:
        """Get a get request from the history from the given URL and params"""
        requests = []
        for request in self.request_history:
            matches = [
                self._get_match_from_url(request=request, url=url),
                self._get_match_from_method(request=request, method=method),
                self._get_match_from_params(request=request, params=params),
                self._get_match_from_response(request=request, response=response),
            ]
            if all(matches):
                requests.append(request)

        return requests

    @staticmethod
    def _get_match_from_url(request: _RequestObjectProxy, url: str | re.Pattern[str] | None = None) -> bool:
        match = url is None
        if not match:
            if isinstance(url, str):
                match = url.strip("/").endswith(request.path.strip("/"))
            elif isinstance(url, re.Pattern):
                match = bool(url.search(request.url))

        return match

    @staticmethod
    def _get_match_from_method(request: _RequestObjectProxy, method: str | None = None) -> bool:
        match = method is None
        if not match:
            # noinspection PyProtectedMember
            match = request._request.method.upper() == method.upper()

        return match

    @staticmethod
    def _get_match_from_params(request: _RequestObjectProxy, params: dict[str, Any] | None = None) -> bool:
        match = params is None
        if not match and request.query:
            for k, v in parse_qs(request.query).items():
                if k in params and str(params[k]) != v[0]:
                    break
                match = True

        return match

    @staticmethod
    def _get_match_from_response(request: _RequestObjectProxy, response: dict[str, Any] | None = None) -> bool:
        match = response is None
        if not match and request.body:
            for k, v in request.json().items():
                if k in response and str(response[k]) != str(v):
                    break
                match = True

        return match
