import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, ContextManager

from aiohttp import ClientResponse
from aioresponses import aioresponses
from aioresponses.core import RequestCall
from yarl import URL

from musify.libraries.remote.core.enum import RemoteIDType, RemoteObjectType

ALL_ID_TYPES = RemoteIDType.all()
ALL_ITEM_TYPES = RemoteObjectType.all()


class RemoteMock(aioresponses, ContextManager, ABC):
    """Generates responses and sets up Remote API requests mock"""

    range_start = 25
    range_stop = 50
    range_max = 200

    limit_lower = 10
    limit_upper = 20
    limit_max = 50

    requests: dict[tuple[str, URL], list[RequestCall]]
    _responses: list[ClientResponse]

    def __enter__(self):
        super().__enter__()
        self.setup_mock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)

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

    @abstractmethod
    def setup_mock(self):
        """Driver to set up mock responses for all endpoints"""
        raise NotImplementedError

    @property
    def total_requests(self) -> int:
        """Returns the total number of requests made to this mock."""
        return sum(len(reqs) for reqs in self.requests.values())

    def reset(self) -> None:
        """Reset the log for the history of requests and responses for by this mock. Does not reset matches."""
        self.requests.clear()
        self._responses.clear()

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

    async def get_requests(
            self,
            method: str | None = None,
            url: str | URL | re.Pattern[str] | None = None,  # matches given after params have been stripped
            params: dict[str, Any] | None = None,
            response: dict[str, Any] | None = None
    ) -> list[tuple[URL, RequestCall, ClientResponse | None]]:
        """Get a get request from the history from the given URL and params"""
        results: list[tuple[URL, RequestCall]] = []
        for (request_method, request_url), requests in self.requests.items():
            for request in requests:
                matches = [
                    self._get_match_from_method(request_method=request_method, method=method),
                    self._get_match_from_url(request_url=request_url, url=url),
                    self._get_match_from_params(request=request, params=params),
                    await self._get_match_from_expected_response(request_url=request_url, response=response),
                ]
                if all(matches):
                    results.append((request_url, request))

        return [(url, request, self._get_response_from_url(url=url)) for url, request in results]

    @staticmethod
    def _get_match_from_method(request_method: str, method: str | None = None) -> bool:
        match = method is None
        if not match:
            # noinspection PyProtectedMember
            match = request_method.upper() == method.upper()

        return match

    @staticmethod
    def _get_match_from_url(request_url: str | URL, url: str | URL | re.Pattern[str] | None = None) -> bool:
        match = url is None
        if not match:
            request_url = str(request_url).rstrip("/").split("?")[0]
            if isinstance(url, str):
                match = request_url == url.split("?")[0]
            elif isinstance(url, URL):
                match = request_url == str(url.with_query(None))
            elif isinstance(url, re.Pattern):
                match = bool(url.search(request_url))

        return match

    @staticmethod
    def _get_match_from_params(request: RequestCall, params: dict[str, Any] | None = None) -> bool:
        match = params is None
        if not match and (request_params := request.kwargs.get("params")):
            for k, v in request_params.items():
                if k in params and str(params[k]) != v:
                    break
                match = True

        return match

    async def _get_match_from_expected_response(
            self, request_url: str | URL, response: dict[str, Any] | None = None
    ) -> bool:
        match = response is None
        if not match:
            response = self._get_response_from_url(url=request_url)
            if response is None:
                return match

            payload = await response.json()
            for k, v in payload.items():
                if k in payload and str(payload[k]) != str(v):
                    break
                match = True

        return match

    def _get_response_from_url(self, url: str | URL) -> ClientResponse | None:
        response = None
        for response in self._responses:
            if str(response.url) == url:
                break

        return response
