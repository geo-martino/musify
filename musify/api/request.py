"""
All operations relating to handling of requests to an API.
"""
import contextlib
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from http import HTTPStatus
from time import sleep
from typing import Any, AsyncContextManager, Self
from urllib.parse import unquote

import aiohttp
from aiohttp import ClientResponse, ClientSession
from yarl import URL

from musify.api.authorise import APIAuthoriser
from musify.api.cache.session import CachedSession
from musify.api.exception import APIError
from musify.log.logger import MusifyLogger
from musify.utils import clean_kwargs


class RequestHandler(AsyncContextManager):
    """
    Generic API request handler using cached responses for GET requests only.
    Caches GET responses for a maximum of 4 weeks by default.
    Handles error responses and backoff on failed requests.
    See :py:class:`APIAuthoriser` for more info on which params to pass to authorise requests.

    :param authoriser: The authoriser to use when authorising requests to the API.
    :param session: The session to use when making requests.
    """

    __slots__ = ("logger", "authoriser", "cache", "session", "backoff_start", "backoff_factor", "backoff_count")

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
        return sum(self.backoff_start * self.backoff_factor ** i for i in range(self.backoff_count + 1))

    def __init__(self, session: ClientSession | None = None, authoriser: APIAuthoriser | None = None):
        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

        #: The :py:class:`APIAuthoriser` object
        self.authoriser = authoriser
        #: The :py:class:`ClientSession` object
        self.session: ClientSession | CachedSession = session if session is not None else ClientSession()

        #: The initial backoff time for failed requests
        self.backoff_start = 0.5
        #: The factor by which to increase backoff time for failed requests i.e. backoff_start ** backoff_factor
        self.backoff_factor = 1.5
        #: The maximum number of request attempts to make before giving up and raising an exception
        self.backoff_count = 10

    async def __aenter__(self) -> Self:
        await self.session.__aenter__()
        await self.authorise()
        return self

    async def __aexit__(self, __exc_type, __exc_value, __traceback) -> None:
        await self.session.__aexit__(__exc_type, __exc_value, __traceback)

    async def authorise(self, force_load: bool = False, force_new: bool = False) -> dict[str, str]:
        """
        Method for API authorisation which tests/refreshes/reauthorises as needed.

        :param force_load: Reloads the token even if it's already been loaded into the object.
            Ignored when force_new is True.
        :param force_new: Ignore saved/loaded token and generate new token.
        :return: Headers for request authorisation.
        :raise APIError: If the token cannot be validated.
        """
        headers = {}
        if self.authoriser is not None:
            headers = await self.authoriser.authorise(force_load=force_load, force_new=force_new)
            self.session.headers.update(headers)

        return headers

    async def close(self) -> None:
        """Close the current session. No more requests will be possible once this has been called."""
        await self.session.close()

    async def request(self, method: str, url: str, *args, **kwargs) -> dict[str, Any]:
        """
        Generic method for handling API requests with back-off on failed requests.
        See :py:func:`request` for more arguments.

        :param method: method for the new :class:`Request` object:
            ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        :param url: URL for the new :class:`Request` object.
        :return: The JSON formatted response or, if JSON formatting not possible, the text response.
        :raise APIError: On any logic breaking error/response.
        """
        backoff = self.backoff_start

        while True:
            async with self._request(method=method, url=url, *args, **kwargs) as response:
                if response is not None and response.status < 400:
                    data = await self._response_as_json(response)
                    break

                waited = None
                if response is not None:
                    await self._log_response(response=response, method=method, url=url)
                    await self._handle_unexpected_response(response=response)
                    waited = await self._handle_wait_time(response=response)

                if not waited and backoff < self.backoff_final:  # exponential backoff
                    self.logger.warning(f"Request failed: retrying in {backoff} seconds...")
                    sleep(backoff)
                    backoff *= self.backoff_factor
                elif waited is False:  # max backoff exceeded
                    raise APIError("Max retries exceeded")
                elif waited is None:  # max backoff exceeded
                    raise APIError("No response received")

        return data

    @contextlib.asynccontextmanager
    async def _request(
            self,
            method: str,
            url: str | URL,
            log_message: str | list[str] = None,
            *args,
            **kwargs
    ) -> ClientResponse | None:
        """Handle logging a request, send the request, and return the response"""
        if isinstance(log_message, str):
            log_message = [log_message]
        elif log_message is None:
            log_message = []

        if isinstance(self.session, CachedSession):
            log_message.append("Cached Request")
        self.log(method=method, url=url, message=log_message, *args, **kwargs)

        if not isinstance(self.session, CachedSession):
            clean_kwargs(aiohttp.request, kwargs)
        if "headers" in kwargs:
            kwargs["headers"].update(self.session.headers)

        try:
            async with self.session.request(method=method.upper(), url=url, *args, **kwargs) as response:
                yield response
        except aiohttp.ClientError as ex:
            self.logger.warning(str(ex))
            yield

    def log(
            self, method: str, url: str | URL, message: str | list = None, level: int = logging.DEBUG, *args, **kwargs
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
        if len(args) > 0:
            log.append(f"Args: ({', '.join(args)})")
        if len(kwargs) > 0:
            log.extend(f"{k.title()}: {str(v):<4}" for k, v in kwargs.items() if v)
        if message:
            log.append(message) if isinstance(message, str) else log.extend(message)

        url = str(url.with_query(None))
        url_pad_map = [30, 40, 70, 100]
        url_pad = next((pad for pad in url_pad_map if len(url) < pad), url_pad_map[-1])

        self.logger.log(
            level=level, msg=f"{method.upper():<7}: {url:<{url_pad}} | {" | ".join(str(part) for part in log)}"
        )

    async def _log_response(self, response: ClientResponse, method: str, url: str) -> None:
        """Log the method, URL, response text, and response headers."""
        response_headers = response.headers
        if isinstance(response.headers, Mapping):  # format headers if JSON
            response_headers = json.dumps(dict(response.headers), indent=2)
        self.logger.warning(
            f"\33[91m{method.upper():<7}: {url} | Code: {response.status} | "
            f"Response text and headers follow:\n"
            f"Response text:\n{await response.text()}\n"
            f"Headers:\n{response_headers}\33[0m"
        )

    async def _handle_unexpected_response(self, response: ClientResponse) -> bool:
        """Handle bad response by extracting message and handling status codes that should raise an exception."""
        message = (await self._response_as_json(response)).get("error", {}).get("message")
        error_message_found = message is not None

        if not error_message_found:
            status = HTTPStatus(response.status)
            message = f"{status.phrase} | {status.description}"

        if 400 <= response.status < 408:
            raise APIError(message, response=response)

        return error_message_found

    async def _handle_wait_time(self, response: ClientResponse) -> bool:
        """Handle when a wait time is included in the response headers."""
        if "retry-after" not in response.headers:
            return False

        wait_time = int(response.headers["retry-after"])
        wait_str = (datetime.now() + timedelta(seconds=wait_time)).strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"\33[91mRate limit exceeded. Retrying again at {wait_str}\33[0m")

        if wait_time > self.timeout:  # exception if too long
            raise APIError(f"Rate limit exceeded and wait time is greater than timeout of {self.timeout} seconds")

        # wait if time is short
        sleep(wait_time)
        return True

    @staticmethod
    async def _response_as_json(response: ClientResponse) -> dict[str, Any]:
        """Format the response to JSON and handle any errors"""
        try:
            data = await response.json()
            return data if isinstance(data, dict) else {}
        except json.decoder.JSONDecodeError:
            return {}

    async def get(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a GET request."""
        kwargs.pop("method", None)
        return await self.request("get", url=url, **kwargs)

    async def post(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a POST request."""
        kwargs.pop("method", None)
        return await self.request("post", url=url, **kwargs)

    async def put(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a PUT request."""
        kwargs.pop("method", None)
        return await self.request("put", url=url, **kwargs)

    async def delete(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a DELETE request."""
        kwargs.pop("method", None)
        return await self.request("delete", url, **kwargs)

    async def options(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends an OPTIONS request."""
        kwargs.pop("method", None)
        return await self.request("options", url=url, **kwargs)

    async def head(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a HEAD request."""
        kwargs.pop("method", None)
        kwargs.setdefault("allow_redirects", False)
        return await self.request("head", url=url, **kwargs)

    async def patch(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a PATCH request."""
        kwargs.pop("method", None)
        return await self.request("patch", url=url, **kwargs)

    def __copy__(self):
        """Do not copy handler"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy handler"""
        return self
