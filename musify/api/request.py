"""
All operations relating to handling of requests to an API.
"""
import asyncio
import contextlib
import json
import logging
from collections.abc import Mapping, Callable
from datetime import datetime, timedelta
from http import HTTPStatus
from time import sleep
from typing import Any, Self
from urllib.parse import unquote

import aiohttp
from aiohttp import ClientResponse, ClientSession
from yarl import URL

from musify.api.authorise import APIAuthoriser
from musify.api.cache.backend import ResponseCache
from musify.api.cache.session import CachedSession
from musify.api.exception import APIError, RequestError
from musify.logger import MusifyLogger
from musify.utils import clean_kwargs


class RequestHandler:
    """
    Generic API request handler using cached responses for GET requests only.
    Caches GET responses for a maximum of 4 weeks by default.
    Handles error responses and backoff on failed requests.
    See :py:class:`APIAuthoriser` for more info on which params to pass to authorise requests.

    :param connector: When called, returns a new session to use when making requests.
    :param authoriser: The authoriser to use when authorising requests to the API.
    """

    __slots__ = (
        "logger",
        "_connector",
        "_session",
        "authoriser",
        "backoff_start",
        "backoff_factor",
        "backoff_count",
        "wait_time",
        "wait_increment",
    )

    @property
    def backoff_final(self) -> float:
        """
        The maximum wait time to retry a request in seconds
        until giving up when applying backoff to failed requests
        """
        return self.backoff_start * self.backoff_factor ** self.backoff_count

    @property
    def timeout(self) -> int:
        """
        When the response gives a time to wait until (i.e. retry-after),
        the program will exit if this time is above this timeout (in seconds)
        """
        return int(sum(self.backoff_start * self.backoff_factor ** i for i in range(self.backoff_count + 1)))

    @property
    def closed(self):
        """Is the stored client session closed."""
        return self._session is None or self._session.closed

    @property
    def session(self) -> ClientSession:
        """The :py:class:`ClientSession` object if it exists and is open."""
        if not self.closed:
            return self._session

    @classmethod
    def create(cls, authoriser: APIAuthoriser | None = None, cache: ResponseCache | None = None, **session_kwargs):
        """Create a new :py:class:`RequestHandler` with an appropriate session ``connector`` given the input kwargs"""
        def connector() -> ClientSession:
            """Create an appropriate session ``connector`` given the input kwargs"""
            if cache is not None:
                return CachedSession(cache=cache, **session_kwargs)
            return ClientSession(**session_kwargs)

        return cls(connector=connector, authoriser=authoriser)

    def __init__(self, connector: Callable[[], ClientSession], authoriser: APIAuthoriser | None = None):
        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

        self._connector = connector
        self._session: ClientSession | CachedSession | None = None

        #: The :py:class:`APIAuthoriser` object
        self.authoriser = authoriser

        #: The initial backoff time in seconds for failed requests
        self.backoff_start = 0.2
        #: The factor by which to increase backoff time for failed requests i.e. backoff_start ** backoff_factor
        self.backoff_factor = 1.932
        #: The maximum number of request attempts to make before giving up and raising an exception
        self.backoff_count = 10

        #: The initial time in seconds to wait after receiving a response from a request
        self.wait_time = 0
        #: The amount to increase the wait time by each time a rate limit is hit i.e. 429 response
        self.wait_increment = 0.1

    async def __aenter__(self) -> Self:
        if self.closed:
            self._session = self._connector()

        await self.session.__aenter__()
        await self.authorise()

        return self

    async def __aexit__(self, __exc_type, __exc_value, __traceback) -> None:
        await self.session.__aexit__(__exc_type, __exc_value, __traceback)
        self._session = None

    async def authorise(self, force_load: bool = False, force_new: bool = False) -> dict[str, str]:
        """
        Method for API authorisation which tests/refreshes/reauthorises as needed.

        :param force_load: Reloads the token even if it's already been loaded into the object.
            Ignored when force_new is True.
        :param force_new: Ignore saved/loaded token and generate new token.
        :return: Headers for request authorisation.
        :raise APIError: If the token cannot be validated.
        """
        if self.closed:
            raise RequestError("Session is closed. Enter the API context to start a new session.")

        headers = {}
        if self.authoriser is not None:
            headers = await self.authoriser(force_load=force_load, force_new=force_new)
            self.session.headers.update(headers)

        return headers

    async def close(self) -> None:
        """Close the current session. No more requests will be possible once this has been called."""
        await self.session.close()

    async def request(self, method: str, url: str | URL, **kwargs) -> dict[str, Any]:
        """
        Generic method for handling API requests with back-off on failed requests.
        See :py:func:`request` for more arguments.

        :param method: method for the request:
            ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        :param url: URL to call.
        :return: The JSON formatted response or, if JSON formatting not possible, the text response.
        :raise APIError: On any logic breaking error/response.
        """
        backoff = self.backoff_start

        while True:
            async with self._request(method=method, url=url, **kwargs) as response:
                if response is None:
                    raise APIError("No response received")

                if response.ok:
                    data = await self._get_json_response(response)
                    break

                await self._log_response(response=response, method=method, url=url)
                handled = await self._handle_bad_response(response=response)
                waited = await self._wait_for_rate_limit_timeout(response=response)

                if handled or waited:
                    continue

                if backoff > self.backoff_final or backoff == 0:
                    raise APIError("Max retries exceeded")

                # exponential backoff
                self.log(method=method, url=url, message=f"Request failed: retrying in {backoff} seconds...")
                sleep(backoff)
                backoff *= self.backoff_factor

        return data

    @contextlib.asynccontextmanager
    async def _request(
            self,
            method: str,
            url: str | URL,
            log_message: str | list[str] = None,
            **kwargs
    ) -> ClientResponse | None:
        """Handle logging a request, send the request, and return the response"""
        if isinstance(log_message, str):
            log_message = [log_message]
        elif log_message is None:
            log_message = []

        if isinstance(self.session, CachedSession):
            log_message.append("Cached Request")
        self.log(method=method, url=url, message=log_message, **kwargs)

        if not isinstance(self.session, CachedSession):
            clean_kwargs(aiohttp.request, kwargs)
        if "headers" in kwargs:
            kwargs["headers"].update(self.session.headers)

        try:
            async with self.session.request(method=method.upper(), url=url, **kwargs) as response:
                yield response
                await asyncio.sleep(self.wait_time)
        except aiohttp.ClientError as ex:
            self.logger.debug(str(ex))
            yield

    def log(
            self, method: str, url: str | URL, message: str | list = None, level: int = logging.DEBUG, **kwargs
    ) -> None:
        """Format and log a request or request adjacent message to the given ``level``."""
        log: list[Any] = []

        url = URL(url)
        if url.query:
            log.extend(f"{k}: {unquote(v):<4}" for k, v in sorted(url.query.items()))
        if kwargs.get("params"):
            log.extend(f"{k}: {v:<4}" for k, v in sorted(kwargs.pop("params").items()))
        if kwargs.get("json"):
            log.extend(f"{k}: {str(v):<4}" for k, v in sorted(kwargs.pop("json").items()))
        if len(kwargs) > 0:
            log.extend(f"{k.title()}: {str(v):<4}" for k, v in kwargs.items() if v)
        if message:
            log.append(message) if isinstance(message, str) else log.extend(message)

        url = str(url.with_query(None))
        url_pad_map = [30, 40, 70, 100]
        url_pad = next((pad for pad in url_pad_map if len(url) < pad), url_pad_map[-1])

        self.logger.log(
            level=level, msg=f"{method.upper():<7}: {url:<{url_pad}} | {" | ".join(map(str, log))}"
        )

    async def _log_response(self, response: ClientResponse, method: str, url: str | URL) -> None:
        """Log the method, URL, response text, and response headers."""
        response_headers = response.headers
        if isinstance(response.headers, Mapping):  # format headers if JSON
            response_headers = json.dumps(dict(response.headers), indent=2)
        self.log(
            method=f"\33[91m{method.upper()}",
            url=url,
            message=[
                f"Status code: {response.status}",
                "Response text and headers follow:\n"
                f"Response text:\n\t{(await response.text()).replace("\n", "\n\t")}\n"
                f"Headers:\n\t{response_headers.replace("\n", "\n\t")}"
                f"\33[0m"
            ]
        )

    async def _handle_bad_response(self, response: ClientResponse) -> bool:
        """Handle bad responses by extracting message and handling status codes that should raise an exception."""
        error_message = (await self._get_json_response(response)).get("error", {}).get("message")
        if error_message is None:
            status = HTTPStatus(response.status)
            error_message = f"{status.phrase} | {status.description}"

        handled = False

        def _log_bad_response(message: str) -> None:
            self.logger.debug(f"Status code: {response.status} | {error_message} | {message}")

        if response.status == 401:
            _log_bad_response("Re-authorising...")
            await self.authorise()
            handled = True
        elif response.status == 429:
            self.wait_time += self.wait_increment
            _log_bad_response(f"Rate limit hit. Increasing wait time between requests to {self.wait_time}")
            handled = True
        elif response.status == 400 <= response.status < 408:
            raise APIError(error_message, response=response)

        return handled

    async def _wait_for_rate_limit_timeout(self, response: ClientResponse) -> bool:
        """Handle rate limits when a 'retry-after' time is included in the response headers."""
        if "retry-after" not in response.headers:
            return False

        wait_time = int(response.headers["retry-after"])
        wait_str = (datetime.now() + timedelta(seconds=wait_time)).strftime("%Y-%m-%d %H:%M:%S")

        if wait_time > self.timeout:  # exception if too long
            raise APIError(
                f"Rate limit exceeded and wait time is greater than timeout of {self.timeout} seconds. "
                f"Retry again at {wait_str}"
            )

        self.logger.info_extra(f"\33[93mRate limit exceeded. Retrying again at {wait_str}\33[0m")
        sleep(wait_time)
        return True

    @staticmethod
    async def _get_json_response(response: ClientResponse) -> dict[str, Any]:
        """Format the response to JSON and handle any errors"""
        try:
            data = await response.json()
            return data if isinstance(data, dict) else {}
        except (aiohttp.ContentTypeError, json.decoder.JSONDecodeError):
            return {}

    async def get(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends a GET request."""
        kwargs.pop("method", None)
        return await self.request("get", url=url, **kwargs)

    async def post(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends a POST request."""
        kwargs.pop("method", None)
        return await self.request("post", url=url, **kwargs)

    async def put(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends a PUT request."""
        kwargs.pop("method", None)
        return await self.request("put", url=url, **kwargs)

    async def delete(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends a DELETE request."""
        kwargs.pop("method", None)
        return await self.request("delete", url, **kwargs)

    async def options(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends an OPTIONS request."""
        kwargs.pop("method", None)
        return await self.request("options", url=url, **kwargs)

    async def head(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends a HEAD request."""
        kwargs.pop("method", None)
        kwargs.setdefault("allow_redirects", False)
        return await self.request("head", url=url, **kwargs)

    async def patch(self, url: str | URL, **kwargs) -> dict[str, Any]:
        """Sends a PATCH request."""
        kwargs.pop("method", None)
        return await self.request("patch", url=url, **kwargs)

    def __copy__(self):
        """Do not copy handler"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy handler"""
        return self
