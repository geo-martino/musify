import json
from typing import Any

import pytest
import requests
from requests import Response
from requests_mock import Mocker
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.response import _Context as Context

from musify.api.authorise import APIAuthoriser
from musify.api.cache.backend.base import ResponseCache
from musify.api.cache.backend.sqlite import SQLiteCache
from musify.api.cache.session import CachedSession
from musify.api.exception import APIError
from musify.api.request import RequestHandler
from tests.api.cache.backend.utils import MockRequestSettings


class TestRequestHandler:

    @pytest.fixture
    def authoriser(self, token: dict[str, Any]) -> APIAuthoriser:
        """Yield a simple :py:class:`APIAuthoriser` object"""
        return APIAuthoriser(name="test", token=token)

    @pytest.fixture
    def cache(self) -> ResponseCache:
        """Yield a simple :py:class:`ResponseCache` object"""
        return SQLiteCache.connect_with_in_memory_db()

    @pytest.fixture
    def request_handler(self, authoriser: APIAuthoriser, cache: ResponseCache) -> RequestHandler:
        """Yield a simple :py:class:`RequestHandler` object"""
        return RequestHandler(authoriser=authoriser, cache=cache)

    @pytest.fixture
    def token(self) -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }

    # noinspection PyTestUnpassedFixture
    def test_init(self, token: dict[str, Any], authoriser: APIAuthoriser, cache: ResponseCache):
        request_handler = RequestHandler(authoriser=authoriser)
        assert request_handler.authoriser.token == token
        assert not isinstance(request_handler.session, CachedSession)

        request_handler = RequestHandler(authoriser=authoriser, cache=cache)
        assert isinstance(request_handler.session, CachedSession)

        request_handler.authorise()
        for k, v in request_handler.authoriser.headers.items():
            assert request_handler.session.headers.get(k) == v

    def test_context_management(self, authoriser: APIAuthoriser):
        with RequestHandler(authoriser=authoriser) as handler:
            for k, v in handler.authoriser.headers.items():
                assert handler.session.headers.get(k) == v

    def test_check_response_codes(self, request_handler: RequestHandler):
        response = Response()

        # error message not found, no fail
        response.status_code = 201
        assert not request_handler._handle_unexpected_response(response=response)

        # error message found, no fail
        expected = {"error": {"message": "request failed"}}
        response._content = json.dumps(expected).encode()
        assert request_handler._handle_unexpected_response(response=response)

        # error message not found, raises exception
        response.status_code = 400
        with pytest.raises(APIError):
            request_handler._handle_unexpected_response(response=response)

    def test_check_for_wait_time(self, request_handler: RequestHandler):
        response = Response()

        # no header
        assert not request_handler._handle_wait_time(response=response)

        # expected key not in headers
        response.headers = {"header key": "header value"}
        assert not request_handler._handle_wait_time(response=response)

        # expected key in headers and time is short
        response.headers = {"retry-after": "1"}
        assert request_handler.timeout >= 1
        assert request_handler._handle_wait_time(response=response)

        # expected key in headers and time too long
        response.headers = {"retry-after": "2000"}
        assert request_handler.timeout < 2000
        with pytest.raises(APIError):
            request_handler._handle_wait_time(response=response)

    def test_response_as_json(self, request_handler: RequestHandler):
        response = Response()
        response._content = "simple text should not be returned".encode()
        assert request_handler._response_as_json(response) == {}

        expected = {"key": "valid json"}
        response._content = json.dumps(expected).encode()
        assert request_handler._response_as_json(response) == expected

    def test_cache_usage(self, request_handler: RequestHandler, requests_mock: Mocker):
        test_url = "http://localhost/test"
        expected_json = {"key": "value"}
        requests_mock.get(test_url, json=expected_json)

        repository = request_handler.cache.create_repository(MockRequestSettings(name="test"))
        request_handler.cache.repository_getter = lambda _, __: repository

        response = request_handler._request(method="GET", url=test_url, persist=False)
        assert response.json() == expected_json
        assert requests_mock.call_count == 1

        key = repository.get_key_from_request(response.request)
        assert repository.get_response(key) is None

        response = request_handler._request(method="GET", url=test_url, persist=True)
        assert response.json() == expected_json
        assert requests_mock.call_count == 2
        assert repository.get_response(key)

        response = request_handler._request(method="GET", url=test_url)
        assert response.json() == expected_json
        assert requests_mock.call_count == 2

        repository.clear()
        response = request_handler._request(method="GET", url=test_url)
        assert response.json() == expected_json
        assert requests_mock.call_count == 3

    def test_request(self, request_handler: RequestHandler, requests_mock: Mocker):
        def raise_error(*_, **__):
            """Just raise a ConnectionError"""
            raise requests.exceptions.ConnectionError()

        # handles connection errors safely
        url = "http://localhost/text_response"
        requests_mock.get(url, text=raise_error)
        assert request_handler._request(method="GET", url=url) is None

        url = "http://localhost/test"
        expected_json = {"key": "value"}

        requests_mock.get(url, json=expected_json)
        assert request_handler.request(method="GET", url=url) == expected_json

        # ignore headers on good status code
        requests_mock.post(url, status_code=200, headers={"retry-after": "2000"}, json=expected_json)
        assert request_handler.request(method="POST", url=url) == expected_json

        # fail on long wait time
        requests_mock.put(url, status_code=429, headers={"retry-after": "2000"})
        assert request_handler.timeout < 2000
        with pytest.raises(APIError):
            request_handler.put(url=url)

        # fail on breaking status code
        requests_mock.delete(url, status_code=400)
        assert request_handler.timeout < 2000
        with pytest.raises(APIError):
            request_handler.delete(method="GET", url=url)

    def test_backoff(self, request_handler: RequestHandler, requests_mock: Mocker):
        url = "http://localhost/test"
        expected_json = {"key": "value"}
        backoff_limit = 3

        # force backoff settings to be short for testing purposes
        request_handler.backoff_start = 0.1
        request_handler.backoff_factor = 2
        request_handler.backoff_count = backoff_limit + 2

        def backoff(_: Request, context: Context) -> dict[str, Any]:
            """Return response based on how many times backoff process has happened"""
            if requests_mock.call_count < backoff_limit:
                context.status_code = 408
                return {"error": {"message": "fail"}}

            context.status_code = 200
            return expected_json

        requests_mock.patch(url, json=backoff)
        assert request_handler.patch(url=url) == expected_json
        assert requests_mock.call_count == backoff_limit
