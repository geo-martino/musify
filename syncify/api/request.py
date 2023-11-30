import json
from collections.abc import Mapping, Iterable
from datetime import datetime as dt
from datetime import timedelta
from http import HTTPStatus
from os.path import dirname, join
from time import sleep
from typing import Any

import requests_cache
from requests.exceptions import ConnectionError
from requests_cache.models.response import BaseResponse

from syncify.utils.logger import Logger
from .authorise import APIAuthoriser
from .exception import APIError


class RequestHandler(APIAuthoriser, Logger):
    """
    Generic API request handler using cached responses for GET requests only.
    Caches GET responses for a maximum of 4 weeks by default.
    Handles error responses and backoff on failed requests.
    See :py:class:`APIAuthoriser` for more info on which params to pass to authorise requests.

    :param cache_path: The path to store the requests session's sqlite cache.
    :param cache_expiry: The expiry time to apply to cached responses after which responses are invalidated.
    :param auth_kwargs: The authorisation kwargs to be passed to :py:class:`APIAuthoriser`.
    """
    backoff_start = 0.5
    backoff_factor = 2
    backoff_count = 10

    def __init__(
            self,
            cache_path: str = join(dirname(dirname(dirname(dirname(__file__)))), ".api_cache", "cache"),
            cache_expiry=timedelta(weeks=4),
            **auth_kwargs
    ):
        APIAuthoriser.__init__(self, **auth_kwargs)

        self.backoff_final = self.backoff_start * self.backoff_factor ** self.backoff_count
        self.timeout = sum(self.backoff_start * self.backoff_factor ** i for i in range(self.backoff_count + 1))

        self.session = requests_cache.CachedSession(
            cache_path, expire_after=cache_expiry, allowable_methods=["GET"]
        )

        self.auth()

    def request(self, method: str, url: str, *args, **kwargs) -> dict[str, Any]:
        """
        Generic method for handling API requests with back-off on failed requests.
        See :py:func:`request` for more arguments.

        :param method: method for the new :class:`Request` object:
            ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        :param url: URL for the new :class:`Request` object.
        :returns: The JSON formatted response or, if JSON formatting not possible, the text response.
        :raises APIError: On any logic breaking error/response.
        """
        kwargs.pop("headers", None)
        response = self._request(method=method, url=url, *args, **kwargs)
        backoff = self.backoff_start

        while response is None or response.status_code >= 400:  # error response code received
            waited = False
            if response is not None:
                self._log_response(response=response, method=method, url=url)
                self._raise_exception(response=response)
                waited = self._check_for_wait_time(response=response)

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
            log_extra: Iterable[str] | None = None,
            *args, **kwargs
    ) -> BaseResponse | None:
        """Handle logging a request, send the request, and return the response"""
        try:  # reauthorise if needed
            headers = self.headers
        except APIError:
            headers = self.auth()

        # format logs
        log = [f"{method.upper():<7}: {url:<{log_pad}}"]
        if log_extra:
            log.extend(log_extra)
        if len(args) > 0:
            log.append(f"Args: ({', '.join(args)})")
        if len(kwargs) > 0:
            log.extend(f"{k.title()}: {v}" for k, v in kwargs.items())
        if use_cache and method.upper() in self.session.settings.allowable_methods:
            log.append("Cached")

        self.logger.debug(" | ".join(log))
        try:
            return self.session.request(
                method=method.upper(), url=url, headers=headers, force_refresh=not use_cache, *args, **kwargs
            )
        except ConnectionError as ex:
            self.logger.warning(ex)
            return

    def _log_response(self, response: BaseResponse, method: str, url: str) -> None:
        """Log the method, url, response text, and response headers."""
        response_headers = response.headers
        if isinstance(response.headers, Mapping):  # format headers if JSON
            response_headers = json.dumps(response.headers, indent=2)
        self.logger.warning(
            f"\33[91m{method.upper():<7}: {url} | Code: {response.status_code} | "
            f"Response text and headers follow:"
            f"\nResponse text:\n{response.text}"
            f"\nHeaders:\n{response_headers} \33[0m"
        )

    def _raise_exception(self, response: BaseResponse) -> None:
        """Check for response status codes that should raise an exception."""
        message = self._response_as_json(response).get("error", {}).get("message")
        if not message:
            status = HTTPStatus(response.status_code)
            message = f"{status.phrase} | {status.description}"

        if response.status_code in [400, 403, 404]:
            raise APIError(message)

    def _check_for_wait_time(self, response: BaseResponse) -> bool:
        """Handle when a wait time is included in the response headers."""
        if "retry-after" in response.headers:  # wait if time is short
            wait_time = int(response.headers["retry-after"])
            wait_str = (dt.now() + timedelta(seconds=wait_time)).strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"\33[91mRate limit exceeded. Retrying again at {wait_str}\33[0m")

            if wait_time > self.timeout:  # exception if too long
                raise APIError(f"Rate limit exceeded and wait time is greater than timeout of {self.timeout} seconds")
            else:
                sleep(wait_time)
                return True

        return False

    @staticmethod
    def _response_as_json(response: BaseResponse) -> dict[str, Any]:
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return {}

    def get(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a GET request."""
        return self.request("get", url=url, **kwargs)

    def post(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a POST request."""
        return self.request("post", url=url, **kwargs)

    def put(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a PUT request."""
        return self.request("put", url=url, **kwargs)

    def delete(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a DELETE request."""
        return self.request("delete", url, **kwargs)

    def options(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends an OPTIONS request."""
        return self.request("options", url=url, **kwargs)

    def head(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a HEAD request."""
        kwargs.setdefault("allow_redirects", False)
        return self.request("head", url=url, **kwargs)

    def patch(self, url: str, **kwargs) -> dict[str, Any]:
        """Sends a PATCH request."""
        return self.request("patch", url=url, **kwargs)
