import json
from datetime import timedelta
from os.path import join
from typing import Any

import pytest
from requests import Response
from requests_cache import OriginalResponse, CachedResponse, CachedSession
from requests_mock import Mocker
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy as Request
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.response import _Context as Context

from syncify.shared.api.request import RequestHandler
from syncify.shared.api.exception import APIError


class TestRequestHandler:

    @pytest.fixture
    def request_handler(self, token: dict[str, Any], tmp_path: str) -> RequestHandler:
        """Yield a simple :py:class:`RequestHandler` object"""
        return RequestHandler(name="test", token=token, cache_path=join(tmp_path, "api_cache"))

    @pytest.fixture
    def token(self) -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }

    # noinspection PyTestUnpassedFixture
    def test_init(self, token: dict[str, Any], tmp_path: str):
        request_handler = RequestHandler(name="test", token=token, cache_path=None)
        assert not isinstance(request_handler.session, CachedSession)

        cache_path = join(tmp_path, "test")
        cache_expiry = timedelta(days=6)
        request_handler = RequestHandler(
            name="test", token=token, cache_expiry=cache_expiry, cache_path=cache_path
        )
        assert isinstance(request_handler.session, CachedSession)
        assert request_handler.token == token
        assert request_handler.session.cache.cache_name == cache_path
        assert request_handler.session.expire_after == cache_expiry

        request_handler.authorise()
        assert request_handler.session.headers == request_handler.headers

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
        url = "http://localhost/test"
        expected_json = {"key": "value"}
        requests_mock.get(url, json=expected_json)

        response = request_handler._request(method="GET", url=url, use_cache=True)
        assert isinstance(response, OriginalResponse)
        assert response.json() == expected_json
        assert requests_mock.call_count == 1

        response = request_handler._request(method="GET", url=url, use_cache=True)
        assert isinstance(response, CachedResponse)
        assert response.json() == expected_json
        assert requests_mock.call_count == 1

        response = request_handler._request(method="GET", url=url, use_cache=False)
        assert isinstance(response, OriginalResponse)
        assert response.json() == expected_json
        assert requests_mock.call_count == 2

    def test_request(self, request_handler: RequestHandler, requests_mock: Mocker):
        def raise_error(*_, **__):
            """Just raise a ConnectionError"""
            raise ConnectionError

        # handles connection errors safely
        url = "http://localhost/text_response"
        requests_mock.get(url, text=raise_error)
        assert request_handler._request(method="GET", url=url) is None

        url = "http://localhost/test"
        expected_json = {"key": "value"}

        requests_mock.get(url, json=expected_json)
        assert request_handler.request(method="GET", url=url, use_cache=False) == expected_json

        # ignore headers on good status code
        requests_mock.post(url, status_code=200, headers={"retry-after": "2000"}, json=expected_json)
        assert request_handler.request(method="POST", url=url, use_cache=False) == expected_json

        # fail on long wait time
        requests_mock.put(url, status_code=429, headers={"retry-after": "2000"})
        assert request_handler.timeout < 2000
        with pytest.raises(APIError):
            request_handler.put(url=url, use_cache=False)

        # fail on breaking status code
        requests_mock.delete(url, status_code=400)
        assert request_handler.timeout < 2000
        with pytest.raises(APIError):
            request_handler.delete(method="GET", url=url, use_cache=False)

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
        assert request_handler.patch(url=url, use_cache=False) == expected_json
        assert requests_mock.call_count == backoff_limit
