import json
from datetime import datetime as dt
from datetime import timedelta
from os.path import dirname, join
from time import sleep
from typing import List, MutableMapping, Any, Optional

import requests_cache
from requests.structures import CaseInsensitiveDict
from requests_cache.models.response import BaseResponse

from syncify.spotify.api.authorise import APIAuthoriser
from syncify.utils.logger import Logger


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
            cache_path, expire_after=cache_expiry, allowable_methods=['GET']
        )

        self.auth()

    def handle(self, method: str, url: str, *args, **kwargs) -> MutableMapping[str, Any]:
        """
        Generic method for handling API requests with back-off on failed requests.
        See :py:func:`request` for more arguments.

        :param method: method for the new :class:`Request` object:
            ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        :param url: URL for the new :class:`Request` object.
        :returns: The JSON formatted response or, if JSON formatting not possible, the text response.
        """
        kwargs.pop("headers", None)
        response = self.request(method=method, url=url, *args, **kwargs)
        backoff = self.backoff_start

        while response.status_code >= 400:
            response_headers = response.headers
            if isinstance(response.headers, CaseInsensitiveDict):
                response_headers = json.dumps(dict(response.headers), indent=2)
            self._logger.warning(f"\33[91m{method.upper():<7}: {url} | Code: {response.status_code} | "
                                 f"Response text and headers follow:"
                                 f"\nResponse text:\n{response.text}"
                                 f"\nHeaders:\n{response_headers} \33[0m")

            message = self._response_as_json(response).get('error', {}).get('message')
            if response.status_code == 403:
                message = message if message else "You are not authorised for this action."
                raise ConnectionError(message)
            elif response.status_code == 404:
                message = message if message else "Resource not found."
                raise ConnectionError(message)

            if 'retry-after' in response.headers:  # wait if time is short
                wait_time = int(response.headers['retry-after'])
                wait_str = (dt.now() + timedelta(seconds=wait_time)).strftime('%Y-%m-%d %H:%M:%S')
                self._logger.info(f"Rate limit exceeded. Retry again at {wait_str}")

                if wait_time > self.timeout:   # exception if too long
                    raise ConnectionError(f"Retry time is greater than timeout of {self.timeout} seconds")

            if backoff < self.backoff_final:
                self._logger.info(f"Retrying in {backoff} seconds...")
                sleep(backoff)
                backoff *= self.backoff_factor
            else:
                raise ConnectionError("Max retries exceeded")

            response = self.request(method=method, url=url, *args, **kwargs)

        return self._response_as_json(response)

    def request(
            self,
            method: str,
            url: str,
            use_cache: bool = True,
            log_pad: int = 43,
            log_extra: Optional[List[str]] = None,
            *args, **kwargs
    ) -> BaseResponse:
        try:
            headers = self.headers
        except TypeError:
            print()
            headers = self.auth()
            print()

        log = [f"{method.upper():<7}: {url:<{log_pad}}"]
        if log_extra:
            log.extend(log_extra)
        if len(args) > 0:
            log.append(f"Args: ({', '.join(args)})")
        if len(kwargs) > 0:
            log.extend(f"{k.title()}: {v}" for k, v in kwargs.items())
        if use_cache and method.upper() in self.session.settings.allowable_methods:
            log.append("Cached")

        self._logger.debug(" | ".join(log))
        return self.session.request(
            method=method.upper(), url=url, headers=headers, force_refresh=not use_cache, *args, **kwargs
        )

    @staticmethod
    def _response_as_json(response: BaseResponse) -> MutableMapping[str, Any]:
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return {}

    def get(self, url: str, **kwargs):
        """Sends a GET request."""
        return self.handle("get", url=url, **kwargs)

    def post(self, url: str, **kwargs):
        """Sends a POST request."""
        return self.handle("post", url=url, **kwargs)

    def put(self, url: str, **kwargs):
        """Sends a PUT request."""
        return self.handle("put", url=url, **kwargs)

    def delete(self, url: str, **kwargs):
        """Sends a DELETE request."""
        return self.handle("delete", url, **kwargs)

    def options(self, url: str, **kwargs):
        """Sends an OPTIONS request."""
        return self.handle("options", url=url, **kwargs)

    def head(self, url: str, **kwargs):
        """Sends a HEAD request."""
        kwargs.setdefault("allow_redirects", False)
        return self.handle("head", url=url, **kwargs)

    def patch(self, url: str, **kwargs):
        """Sends a PATCH request."""
        return self.handle("patch", url=url, **kwargs)
