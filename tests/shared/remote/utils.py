import re
from abc import abstractmethod
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs

from requests_mock import Mocker
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy

from syncify.shared.remote.enum import RemoteIDType, RemoteObjectType

ALL_ID_TYPES = RemoteIDType.all()
ALL_ITEM_TYPES = RemoteObjectType.all()


class RemoteMock(Mocker):
    """Generates responses and sets up Remote API requests mock"""

    @property
    @abstractmethod
    def item_type_map(self) -> dict[RemoteObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`RemoteObjectType` to the mocked items mapped as {``id``: <item>}"""
        raise NotImplementedError

    @property
    @abstractmethod
    def item_type_map_user(self) -> dict[RemoteObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`RemoteObjectType` to the mocked user items mapped as {``id``: <item>}"""
        raise NotImplementedError

    @staticmethod
    def calculate_pages(limit: int, total: int) -> int:
        """
        Calculates the numbers of a pages that need to be called from a given ``total`` and ``limit`` per page
        to get all items related to this response.
        """
        return total // limit + (total % limit > 0)  # round up

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
            match_url = url is None
            if not match_url:
                if isinstance(url, str):
                    match_url = url.strip("/").endswith(request.path.strip("/"))
                elif isinstance(url, re.Pattern):
                    match_url = bool(url.search(request.url))

            match_method = method is None
            if not match_method:
                # noinspection PyProtectedMember
                match_method = request._request.method.upper() == method.upper()

            match_params = params is None
            if not match_params and request.query:
                for k, v in parse_qs(request.query).items():
                    if k in params and str(params[k]) != v[0]:
                        break
                    match_params = True

            match_response = response is None
            if not match_response and request.body:
                for k, v in request.json().items():
                    if k in response and str(response[k]) != str(v):
                        break
                    match_response = True

            if match_url and match_method and match_params and match_response:
                requests.append(request)

        return requests
