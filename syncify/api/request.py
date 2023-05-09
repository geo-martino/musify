import json
from datetime import datetime as dt
from datetime import timedelta
from os.path import dirname, join
from time import sleep
from typing import MutableMapping, Any

import requests_cache
from requests.structures import CaseInsensitiveDict
from requests_cache.models.response import BaseResponse

from syncify.api.authorise import APIAuthoriser
from syncify.utils.logger import Logger


class RequestHandler(APIAuthoriser, Logger):
    """
    Generic API request handler using cached responses for GET requests only.
    Caches GET responses for a maximum of 4 weeks.
    Handles error responses and backoff on failed requests.
    See :py:class:`APIAuthoriser` for more info on which params to pass to authorise requests.

    :param cache_path: The path to store the requests session's sqlite cache.
    :param auth_kwargs: The authorisation kwargs to be passed to :py:class:`APIAuthoriser`.
    """
    backoff_start = 0.5
    backoff_factor = 2
    backoff_count = 10

    default_cache = join(dirname(dirname(dirname(__file__))), ".api_cache", "cache")

    def __init__(self, cache_path: str = default_cache, **auth_kwargs):
        APIAuthoriser.__init__(self, **auth_kwargs)

        self.backoff_final = self.backoff_start * self.backoff_factor ** self.backoff_count
        self.timeout = sum(self.backoff_start * self.backoff_factor ** i for i in range(self.backoff_count + 1))

        self.session = requests_cache.CachedSession(
            cache_path, expire_after=timedelta(weeks=4), allowable_methods=['GET']
        )

        self.auth()

    def request(self, method: str, url: str, use_cache: bool = True, *args, **kwargs) -> MutableMapping[str, Any]:
        """
        Generic method for handling API requests with back-off on failed requests.
        See :py:func:`request` for more arguments.

        :param method: method for the new :class:`Request` object:
            ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        :param url: URL for the new :class:`Request` object.
        :returns: The JSON formatted response or, if JSON formatting not possible, the text response.
        """
        try:
            headers = self.headers
        except TypeError:
            headers = self.auth()

        kwargs.pop("headers", None)
        response = self.session.request(
            method=method.upper(), url=url, headers=headers, force_refresh=not use_cache, *args, **kwargs
        )
        backoff = self.backoff_start

        while response.status_code >= 400:
            response_headers = response.headers
            if isinstance(response.headers, CaseInsensitiveDict):
                response_headers = json.dumps(dict(response.headers), indent=2)
            self._logger.warning(f"\33[91mEndpoint: {url} | Code: {response.status_code} | "
                                 f"Response text and headers follow:"
                                 f"\nResponse text:\n{response.text}"
                                 f"\nHeaders:\n{response_headers}\33[0m")

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

            response = self.session.request(method=method.upper(), url=url, headers=self.auth(), *args, **kwargs)

        return self._response_as_json(response)

    @staticmethod
    def _response_as_json(response: BaseResponse) -> MutableMapping[str, Any]:
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return {}

    def get(self, url: str, **kwargs):
        """Sends a GET request."""
        return self.request("get", url=url, **kwargs)

    def post(self, url: str, **kwargs):
        """Sends a POST request."""
        return self.request("post", url=url, **kwargs)

    def put(self, url: str, **kwargs):
        """Sends a PUT request."""
        return self.request("put", url=url, **kwargs)

    def delete(self, url: str, **kwargs):
        """Sends a DELETE request."""
        return self.request("delete", url, **kwargs)

    def options(self, url: str, **kwargs):
        """Sends an OPTIONS request."""
        return self.request("options", url=url, **kwargs)

    def head(self, url: str, **kwargs):
        """Sends a HEAD request."""
        kwargs.setdefault("allow_redirects", False)
        return self.request("head", url=url, **kwargs)

    def patch(self, url: str, **kwargs):
        """Sends a PATCH request."""
        return self.request("patch", url=url, **kwargs)
