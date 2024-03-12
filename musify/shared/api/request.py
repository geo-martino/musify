"""
All operations relating to handling of requests to an API.
"""

import json
from collections.abc import Mapping, Iterable
from datetime import datetime as dt
from datetime import timedelta
from http import HTTPStatus
from time import sleep
from typing import Any

import requests
from requests import Response, Session
from requests_cache import CachedSession

from musify.shared.api.authorise import APIAuthoriser
from musify.shared.api.exception import APIError


class RequestHandler(APIAuthoriser):
    """
    Generic API request handler using cached responses for GET requests only.
    Caches GET responses for a maximum of 4 weeks by default.
    Handles error responses and backoff on failed requests.
    See :py:class:`APIAuthoriser` for more info on which params to pass to authorise requests.

    :param cache_path: The path to store the requests session's sqlite cache.
    :param cache_expiry: The expiry time to apply to cached responses after which responses are invalidated.
    :param auth_kwargs: The authorisation kwargs to be passed to :py:class:`APIAuthoriser`.
    """

    __slots__ = ("session", "__dict__")

    #: The initial backoff time for failed requests
    backoff_start = 0.5
    #: The factor by which to increase backoff time for failed requests i.e. backoff_start ** backoff_factor
    backoff_factor = 2
    #: The maximum number of request attempts to make before giving up and raising an exception
    backoff_count = 10

    @property
    def backoff_final(self) -> int:
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

    def __init__(self, cache_path: str | None = None, cache_expiry=timedelta(weeks=4), **auth_kwargs):
        super().__init__(**auth_kwargs)

        #: The :py:class:`Session` or :py:class:`CachedSession` object
        self.session: CachedSession | Session
        if cache_path:
            self.logger.debug(f"Setting up requests cache: {cache_path}")
            self.session = CachedSession(cache_path, expire_after=cache_expiry, allowable_methods=["GET"])
        else:
            self.session = Session()

    def authorise(self, force_load: bool = False, force_new: bool = False) -> dict[str, str]:
        headers = super().authorise(force_load=force_load, force_new=force_new)
        self.session.headers.update(headers)
        return headers

    def request(self, method: str, url: str, *args, **kwargs) -> dict[str, Any]:
        """
        Generic method for handling API requests with back-off on failed requests.
        See :py:func:`request` for more arguments.

        :param method: method for the new :class:`Request` object:
            ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        :param url: URL for the new :class:`Request` object.
        :return: The JSON formatted response or, if JSON formatting not possible, the text response.
        :raise APIError: On any logic breaking error/response.
        """
        kwargs.pop("headers", None)
        response = self._request(method=method, url=url, *args, **kwargs)
        backoff = self.backoff_start

        while response is None or response.status_code >= 400:  # error response code received
            waited = False
            if response is not None:
                self._log_response(response=response, method=method, url=url)
                self._handle_unexpected_response(response=response)
                waited = self._handle_wait_time(response=response)

            if not waited and backoff < self.backoff_final:  # exponential backoff
                self.logger.warning(f"Request failed: retrying in {backoff} seconds...")
                sleep(backoff)
                backoff *= self.backoff_factor
            elif not waited:  # max backoff exceeded
                raise APIError("Max retries exceeded")

            response = self._request(method=method, url=url, *args, **kwargs)

        return self._response_as_json(response)

    def _request(
            self,
            method: str,
            url: str,
            use_cache: bool = True,
            log_pad: int = 43,
            log_extra: Iterable[str] = (),
            *args,
            **kwargs
    ) -> Response | None:
        """Handle logging a request, send the request, and return the response"""
        # format logs
        log = [f"{method.upper():<7}: {url:<{log_pad}}"]
        if log_extra:
            log.extend(log_extra)
        if len(args) > 0:
            log.append(f"Args: ({', '.join(args)})")
        if len(kwargs) > 0:
            log.extend(f"{k.title()}: {v}" for k, v in kwargs.items())
        if use_cache and isinstance(self.session, CachedSession):
            if method.upper() in self.session.settings.allowable_methods:
                log.append("Cached")

        headers = self.session.headers
        if "headers" in kwargs:
            headers = kwargs.pop("headers") | self.session.headers

        self.logger.debug(" | ".join(log))
        try:
            if not isinstance(self.session, CachedSession):
                return self.session.request(method=method.upper(), url=url, headers=headers, *args, **kwargs)
            return self.session.request(
                method=method.upper(), force_refresh=not use_cache, url=url, headers=headers, *args, **kwargs
            )
        except requests.exceptions.ConnectionError as ex:
            self.logger.warning(str(ex))
            return

    def _log_response(self, response: Response, method: str, url: str) -> None:
        """Log the method, URL, response text, and response headers."""
        response_headers = response.headers
        if isinstance(response.headers, Mapping):  # format headers if JSON
            response_headers = json.dumps(dict(response.headers), indent=2)
        self.logger.warning(
            f"\33[91m{method.upper():<7}: {url} | Code: {response.status_code} | "
            f"Response text and headers follow:\n"
            f"Response text:\n{response.text}\n"
            f"Headers:\n{response_headers}\33[0m"
        )

    def _handle_unexpected_response(self, response: Response) -> bool:
        """Handle bad response by extracting message and handling status codes that should raise an exception."""
        message = self._response_as_json(response).get("error", {}).get("message")
        error_message_found = message is not None

        if not error_message_found:
            status = HTTPStatus(response.status_code)
            message = f"{status.phrase} | {status.description}"

        if 400 <= response.status_code < 408:
            raise APIError(message, response=response)

        return error_message_found

    def _handle_wait_time(self, response: Response) -> bool:
        """Handle when a wait time is included in the response headers."""
        if "retry-after" not in response.headers:
            return False

        wait_time = int(response.headers["retry-after"])
        wait_str = (dt.now() + timedelta(seconds=wait_time)).strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"\33[91mRate limit exceeded. Retrying again at {wait_str}\33[0m")

        if wait_time > self.timeout:  # exception if too long
            raise APIError(f"Rate limit exceeded and wait time is greater than timeout of {self.timeout} seconds")

        # wait if time is short
        sleep(wait_time)
        return True

    @staticmethod
    def _response_as_json(response: Response) -> dict[str, Any]:
        """Format the response to JSON and handle any errors"""
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return {}

    def get(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a GET request."""
        kwargs.pop("method", None)
        return self.request("get", url=url, **kwargs)

    def post(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a POST request."""
        kwargs.pop("method", None)
        return self.request("post", url=url, **kwargs)

    def put(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a PUT request."""
        kwargs.pop("method", None)
        return self.request("put", url=url, **kwargs)

    def delete(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a DELETE request."""
        kwargs.pop("method", None)
        return self.request("delete", url, **kwargs)

    def options(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends an OPTIONS request."""
        kwargs.pop("method", None)
        return self.request("options", url=url, **kwargs)

    def head(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a HEAD request."""
        kwargs.pop("method", None)
        kwargs.setdefault("allow_redirects", False)
        return self.request("head", url=url, **kwargs)

    def patch(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a PATCH request."""
        kwargs.pop("method", None)
        return self.request("patch", url=url, **kwargs)

    def __copy__(self):
        """Do not copy handler"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy handler"""
        return self
