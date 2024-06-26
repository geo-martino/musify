import json
from time import perf_counter
from typing import Any

import aiohttp
import pytest
from aiohttp import ClientRequest
from aioresponses import aioresponses, CallbackResult
from yarl import URL

from musify.api.authorise import APIAuthoriser
from musify.api.cache.backend.base import ResponseCache
from musify.api.cache.backend.sqlite import SQLiteCache
from musify.api.cache.response import CachedResponse
from musify.api.cache.session import CachedSession
from musify.api.exception import APIError, RequestError
from musify.api.request import RequestHandler
from tests.api.cache.backend.utils import MockRequestSettings


class TestRequestHandler:

    @pytest.fixture
    def url(self) -> URL:
        """Yield a simple :py:class:`URL` object"""
        return URL("http://test.com")

    @pytest.fixture
    def cache(self) -> ResponseCache:
        """Yield a simple :py:class:`ResponseCache` object"""
        return SQLiteCache.connect_with_in_memory_db()

    @pytest.fixture
    def authoriser(self, token: dict[str, Any]) -> APIAuthoriser:
        """Yield a simple :py:class:`APIAuthoriser` object"""
        return APIAuthoriser(name="test", token=token)

    @pytest.fixture
    def request_handler(self, authoriser: APIAuthoriser, cache: ResponseCache) -> RequestHandler:
        """Yield a simple :py:class:`RequestHandler` object"""
        return RequestHandler.create(
            authoriser=authoriser, cache=cache, headers={"Content-Type": "application/json"}
        )

    @pytest.fixture
    def token(self) -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }

    async def test_init(self, token: dict[str, Any], authoriser: APIAuthoriser, cache: ResponseCache):
        handler = RequestHandler.create(authoriser=authoriser, cache=cache)
        assert handler.authoriser.token == token
        assert not isinstance(handler.session, CachedSession)

        handler = RequestHandler.create(authoriser=authoriser, cache=cache)
        assert handler.closed

    async def test_context_management(self, request_handler: RequestHandler):
        with pytest.raises(RequestError):
            await request_handler.authorise()

        async with request_handler as handler:
            assert isinstance(handler.session, CachedSession)

            for k, v in handler.authoriser.headers.items():
                assert handler.session.headers.get(k) == v

    async def test_bad_response_handling(self, request_handler: RequestHandler, url: URL):
        headers = {"Content-Type": "application/json"}
        request = ClientRequest(method="GET", url=url, headers=headers)

        # error message not found, no fail
        response = CachedResponse(request=request, data="")
        response.status = 201
        assert not await request_handler._handle_bad_response(response=response)

        # error message found, no fail
        expected = {"error": {"message": "request failed"}}
        response = CachedResponse(request=request, data=json.dumps(expected))
        assert not await request_handler._handle_bad_response(response=response)

        # error message not found, raises exception
        response.status = 400
        with pytest.raises(APIError):
            await request_handler._handle_bad_response(response=response)

        # increases wait time on responses with 'too many requests'
        wait_initial = request_handler.wait_time
        response.status = 429
        for i in range(1, 5):
            assert await request_handler._handle_bad_response(response=response)
            assert request_handler.wait_time == wait_initial + i * request_handler.wait_increment

    async def test_rate_limit_handling(self, request_handler: RequestHandler, url: URL):
        # no header
        request = ClientRequest(method="GET", url=URL("http://test.com"))
        response = CachedResponse(request, data="")
        assert not await request_handler._wait_for_rate_limit_timeout(response=response)

        # expected key not in headers
        headers = {"header key": "header value"}
        request = ClientRequest(method="GET", url=url, headers=headers)
        response = CachedResponse(request, data="")
        assert not await request_handler._wait_for_rate_limit_timeout(response=response)

        # expected key in headers and time is short
        headers = {"retry-after": "1"}
        request = ClientRequest(method="GET", url=url, headers=headers)
        response = CachedResponse(request, data="")
        assert request_handler.timeout >= 1
        assert await request_handler._wait_for_rate_limit_timeout(response=response)

        # expected key in headers and time too long
        headers = {"retry-after": "2000"}
        request = ClientRequest(method="GET", url=url, headers=headers)
        response = CachedResponse(request, data="")
        assert request_handler.timeout < 2000
        with pytest.raises(APIError):
            await request_handler._wait_for_rate_limit_timeout(response=response)

    async def test_get_json_response(self, request_handler: RequestHandler, url: URL):
        request = ClientRequest(method="GET", url=url, headers={"Content-Type": "application/json"})
        response = CachedResponse(request=request, data="simple text should not be returned")
        assert await request_handler._get_json_response(response) == {}

        expected = {"key": "valid json"}
        response = CachedResponse(request=request, data=json.dumps(expected))
        assert await request_handler._get_json_response(response) == expected

    # noinspection PyTestUnpassedFixture
    async def test_cache_usage(self, request_handler: RequestHandler, requests_mock: aioresponses):
        url = "http://localhost/test"
        expected_json = {"key": "value"}
        requests_mock.get(url, payload=expected_json, repeat=True)

        async with request_handler as handler:
            repository = await handler.session.cache.create_repository(MockRequestSettings(name="test"))
            handler.session.cache.repository_getter = lambda _, __: repository

            async with handler._request(method="GET", url=url, persist=False) as response:
                assert await response.json() == expected_json
                requests_mock.assert_called_once()

            key = repository.get_key_from_request(response.request_info)
            assert await repository.get_response(key) is None

            async with handler._request(method="GET", url=url, persist=True) as response:
                assert await response.json() == expected_json
            assert sum(map(len, requests_mock.requests.values())) == 2
            assert await repository.get_response(key)

            async with handler._request(method="GET", url=url) as response:
                assert await response.json() == expected_json
            assert sum(map(len, requests_mock.requests.values())) == 2

            await repository.clear()
            async with handler._request(method="GET", url=url) as response:
                assert await response.json() == expected_json
            assert sum(map(len, requests_mock.requests.values())) == 3

    async def test_request(self, request_handler: RequestHandler, requests_mock: aioresponses):
        def raise_error(*_, **__):
            """Just raise a ConnectionError"""
            raise aiohttp.ClientConnectionError()

        # handles connection errors safely
        url = "http://localhost/text_response"
        requests_mock.get(url, callback=raise_error, repeat=True)
        async with request_handler as handler:
            async with handler._request(method="GET", url=url) as response:
                assert response is None

            url = "http://localhost/test"
            expected_json = {"key": "value"}

            requests_mock.get(url, payload=expected_json)
            assert await handler.request(method="GET", url=url) == expected_json

            # still process wait time on good status code
            requests_mock.post(url, status=200, headers={"retry-after": "2000"}, payload=expected_json)
            with pytest.raises(APIError):
                assert await handler.request(method="POST", url=url) == expected_json

            # still handles bad response on good status code
            requests_mock.post(url, status=200, headers={"error": {"status": 404}}, payload=expected_json)
            with pytest.raises(APIError):
                assert await handler.request(method="PATCH", url=url) == expected_json

            # fail on long wait time
            requests_mock.put(url, status=429, headers={"retry-after": "2000"})
            assert handler.timeout < 2000
            with pytest.raises(APIError):
                await handler.put(url=url)

            # fail on breaking status code
            requests_mock.delete(url, status=400)
            assert handler.timeout < 2000
            with pytest.raises(APIError):
                await handler.delete(method="GET", url=url)

    async def test_backoff(self, request_handler: RequestHandler, requests_mock: aioresponses):
        url = "http://localhost/test"
        expected_json = {"key": "value"}
        backoff_limit = 3

        # force wait time settings off to isolate backoff waiting only
        request_handler.wait_time = 0
        request_handler.wait_increment = 0

        # force backoff settings to be short for testing purposes
        request_handler.backoff_start = 0.1
        request_handler.backoff_factor = 2
        request_handler.backoff_count = backoff_limit + 2

        def callback(method: str, *_, **__) -> CallbackResult:
            """Modify mock response based on how many times backoff process has happened"""
            if sum(map(len, requests_mock.requests.values())) < backoff_limit:
                payload = {"error": {"message": "fail"}}
                return CallbackResult(method=method, status=408, payload=payload)

            return CallbackResult(method=method, status=200, payload=expected_json)

        requests_mock.patch(url, callback=callback, repeat=True)
        async with request_handler as handler:
            assert await handler.patch(url=url) == expected_json
        assert sum(map(len, requests_mock.requests.values())) == backoff_limit

    async def test_wait_time_is_incremented(self, request_handler: RequestHandler, requests_mock: aioresponses):
        url = "http://localhost/test"
        wait_limit = 0.6

        # force backoff settings to be very low to isolate wait time waiting only
        request_handler.backoff_start = 0.001
        request_handler.backoff_factor = 1
        request_handler.backoff_count = 10

        # set wait time settings and get expected total time
        wait_time = 0.1
        request_handler.wait_time = wait_time
        request_handler.wait_increment = 0.2
        request_handler.wait_max = 999

        wait_total_expected = request_handler.wait_time
        while wait_time < wait_limit:
            wait_time += request_handler.wait_increment
            wait_total_expected += wait_time

        def callback(method: str, *_, **__) -> CallbackResult:
            """Modify mock response based on current handler wait time settings"""
            if request_handler.wait_time < wait_limit:
                payload = {"error": {"message": "too many requests"}}
                return CallbackResult(method=method, status=429, payload=payload)

            return CallbackResult(method=method, status=200)

        start_time = perf_counter()
        requests_mock.head(url, callback=callback, repeat=True)
        async with request_handler as handler:
            await handler.head(url=url)

        assert perf_counter() - start_time >= wait_total_expected
        assert request_handler.wait_time > wait_limit

    async def test_wait_time_is_capped(self, request_handler: RequestHandler, requests_mock: aioresponses):
        url = "http://localhost/test"

        # does not increment wait time past the max allowed time
        wait_time = 0.1
        request_handler.wait_time = wait_time
        request_handler.wait_increment = 0.2
        request_handler.wait_max = request_handler.wait_time + (request_handler.wait_increment * 2)

        count = 0

        def callback(method: str, *_, **__) -> CallbackResult:
            """Modify mock response based on current handler wait time settings"""
            nonlocal count

            if count < 5:
                count += 1
                payload = {"error": {"message": "too many requests"}}
                return CallbackResult(method=method, status=429, payload=payload)

            return CallbackResult(method=method, status=200)

        requests_mock.get(url, callback=callback, repeat=True)
        async with request_handler as handler:
            await handler.get(url=url)

        assert request_handler.wait_time == request_handler.wait_max
