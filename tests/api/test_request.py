import json
from datetime import timedelta
from os.path import join
from typing import Any

import pytest
from requests import Response
from requests_cache import OriginalResponse, CachedResponse
from requests_mock import Mocker

from syncify.api import RequestHandler
from syncify.api.exception import APIError


class TestRequestHandler:

    @staticmethod
    @pytest.fixture
    def request_handler(token: dict[str, Any], tmp_path: str) -> RequestHandler:
        """Yield a simple :py:class:`APIAuthoriser` object"""
        return RequestHandler(name="test", token=token, cache_path=join(tmp_path, "api_cache"))

    @staticmethod
    @pytest.fixture
    def token() -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }

    @staticmethod
    def test_init(token: dict[str, Any], tmp_path: str):
        cache_path = join(tmp_path, "test")
        cache_expiry = timedelta(days=6)
        request_handler = RequestHandler(
            name="test", token=token, cache_expiry=cache_expiry, cache_path=cache_path
        )
        assert request_handler.token == token
        assert request_handler.session.cache.cache_name == cache_path
        assert request_handler.session.expire_after == cache_expiry
        assert request_handler.session.headers == request_handler.headers

    @staticmethod
    def test_check_response_codes(request_handler: RequestHandler):
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

    @staticmethod
    def test_check_for_wait_time(request_handler: RequestHandler):
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

    @staticmethod
    def test_response_as_json(request_handler: RequestHandler):
        response = Response()
        response._content = "simple text should not be returned".encode()
        assert request_handler._response_as_json(response) == {}

        expected = {"key": "valid json"}
        response._content = json.dumps(expected).encode()
        assert request_handler._response_as_json(response) == expected

    @staticmethod
    def test_cache_usage(request_handler: RequestHandler, requests_mock: Mocker):
        url = "http://localhost/test"
        expected_json = {"key": "value"}

        requests_mock.get(url, json=expected_json)
        assert isinstance(request_handler._request(method="GET", url=url, use_cache=True), OriginalResponse)
        assert isinstance(request_handler._request(method="GET", url=url, use_cache=True), CachedResponse)
        assert isinstance(request_handler._request(method="GET", url=url, use_cache=False), OriginalResponse)

    @staticmethod
    def test_request(request_handler: RequestHandler, requests_mock: Mocker):
        url = "http://localhost/test"
        expected_json = {"key": "value"}

        # no mock request set
        requests_mock.stop()
        assert request_handler._request(method="GET", url=url) is None

        requests_mock.start()
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

    @staticmethod
    def test_backoff(request_handler: RequestHandler, requests_mock: Mocker):
        url = "http://localhost/test"
        expected_json = {"key": "value"}
        backoff_count = 0
        backoff_count_max = 3

        # force backoff settings to be short for testing purposes
        request_handler.backoff_start = 0.2
        request_handler.backoff_factor = 2
        request_handler.backoff_count = 5

        def backoff(_, context) -> dict[str, Any]:
            """Return response based on how many times backoff process has happened"""
            nonlocal backoff_count
            if backoff_count < backoff_count_max:
                context.status_code = 408
                backoff_count += 1
                return {"error": {"message": "fail"}}

            context.status_code = 200
            return expected_json

        requests_mock.patch(url, json=backoff)
        assert request_handler.patch(url=url, use_cache=False) == expected_json
        assert backoff_count == backoff_count_max
