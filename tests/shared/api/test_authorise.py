import json
import os
import socket
from datetime import datetime, timedelta
from os.path import join
from typing import Any
from urllib.parse import urlparse, parse_qs

import pytest
from pytest_mock import MockerFixture
from requests_mock import Mocker

from syncify import MODULE_ROOT
from syncify.shared.api.authorise import APIAuthoriser
from syncify.shared.api.exception import APIError
from tests.shared.api.utils import path_token


class TestAPIAuthoriser:

    refresh_test_keys = ("granted_at", "expires_at", "refresh_token")

    @pytest.fixture
    def authoriser(self) -> APIAuthoriser:
        """Yield an authorised :py:class:`SpotifyAPI` object"""
        return APIAuthoriser(name="test")

    @pytest.fixture
    def token(self) -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }

    @pytest.fixture(params=[path_token])
    def token_file_path(self, path: str) -> str:
        """Yield the temporary path for the token JSON file"""
        return path

    # noinspection PyStatementEffect
    def test_properties(self, authoriser: APIAuthoriser, token: dict[str, Any]):
        with pytest.raises(APIError):
            authoriser.headers

        authoriser.token = token
        authoriser.header_key = "Authorization"
        authoriser.header_prefix = "Bearer "
        authoriser.header_extra = {}
        authoriser.token_key_path = ("access_token",)
        assert "access_token" in authoriser.token
        assert authoriser.headers == {"Authorization": f"Bearer {authoriser.token["access_token"]}"}

        extra = {"extra": "value"}
        authoriser.header_extra = extra
        assert authoriser.headers == {"Authorization": f"Bearer {authoriser.token["access_token"]}"} | extra

        authoriser.token_key_path = ("does", "not", "exist")
        with pytest.raises(APIError):
            authoriser.headers

        assert authoriser.token == token
        assert authoriser.token_safe != token

    def test_load_token(self, authoriser: APIAuthoriser, token_file_path: str):
        # just check it doesn't fail when no path given
        authoriser.token = None
        authoriser.token_file_path = None
        assert authoriser.load_token() is None

        authoriser.token_file_path = token_file_path
        token = authoriser.load_token()
        assert token["access_token"] == "fake access token"
        assert token["token_type"] == "Bearer"
        assert token["scope"] == "test-read"

    def test_save_token(self, authoriser: APIAuthoriser, token: dict[str, Any], tmp_path: str):
        # just check it doesn't fail when no path given
        authoriser.token = None
        authoriser.token_file_path = None
        authoriser.save_token()

        authoriser.token_file_path = join(tmp_path, "token.json")
        authoriser.save_token()
        assert not os.path.exists(authoriser.token_file_path)

        authoriser.token = token
        authoriser.save_token()

        with open(authoriser.token_file_path, "r") as f:
            token_saved = json.load(f)

        assert token == token_saved

    def test_user_auth(self, authoriser: APIAuthoriser, mocker: MockerFixture, requests_mock: Mocker):
        user_url = f"http://{APIAuthoriser._user_auth_socket_address}:{APIAuthoriser._user_auth_socket_port + 1}"
        authoriser.auth_args = {"url": ""}
        authoriser.user_args = {"url": user_url}

        redirect_uri = f"http://{authoriser._user_auth_socket_address}:{authoriser._user_auth_socket_port}/"
        code = "test-code"
        response = f"GET /?code={code}&state=test HTTP/1.1"

        def check_url(url: str):
            """Check the URL given to the webopen call"""
            assert url.startswith(user_url)
            assert parse_qs(urlparse(url).query)["redirect_uri"][0] == redirect_uri

        socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        requests_mock.post(user_url)
        mocker.patch(f"{MODULE_ROOT}.shared.api.authorise.webopen", new=check_url)
        mocker.patch.object(socket.socket, attribute="accept", return_value=(socket_listener, None))
        mocker.patch.object(socket.socket, attribute="send")
        mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        authoriser._authorise_user()
        assert authoriser.auth_args["data"]["code"] == code
        assert authoriser.auth_args["data"]["redirect_uri"] == redirect_uri

    def test_request_token_1(self, authoriser: APIAuthoriser, token: dict[str, Any], requests_mock: Mocker):
        authoriser.auth_args = {
            "url": f"http://{APIAuthoriser._user_auth_socket_address}:{APIAuthoriser._user_auth_socket_port + 1}",
            "data": {"grant_type": "authorization_code", "code": None},
        }
        requests_mock.post(authoriser.auth_args["url"], json=token)

        result = authoriser._request_token(**authoriser.auth_args)
        assert {k: v for k, v in result.items() if k not in self.refresh_test_keys} == token
        assert "granted_at" in result
        assert "expires_at" not in result
        assert "refresh_token" not in result

    def test_request_token_2(self, authoriser: APIAuthoriser, token: dict[str, Any], requests_mock: Mocker):
        authoriser.auth_args = {
            "url": f"http://{APIAuthoriser._user_auth_socket_address}:{APIAuthoriser._user_auth_socket_port + 1}",
            "data": {"grant_type": "authorization_code", "code": None},
        }
        authoriser.token = {"refresh_token": "new token"}
        expires_in_token = {"expires_in": 3600}
        requests_mock.post(authoriser.auth_args["url"], json=token | expires_in_token)

        result = authoriser._request_token(**authoriser.auth_args)
        assert {k: v for k, v in result.items() if k not in self.refresh_test_keys} == token | expires_in_token
        assert "granted_at" in result
        assert "expires_at" in result
        assert result["refresh_token"] == authoriser.token["refresh_token"]

    def test_request_token_3(self, authoriser: APIAuthoriser, token: dict[str, Any], requests_mock: Mocker):
        authoriser.auth_args = {
            "url": f"http://{APIAuthoriser._user_auth_socket_address}:{APIAuthoriser._user_auth_socket_port + 1}",
            "data": {"grant_type": "authorization_code", "code": None},
        }
        response = token | {"refresh_token": "received token"}
        requests_mock.post(authoriser.auth_args["url"], json=response)

        result = authoriser._request_token(**authoriser.auth_args)
        assert {k: v for k, v in result.items() if k not in self.refresh_test_keys} == token
        assert "granted_at" in result
        assert "expires_at" not in result
        assert result["refresh_token"] == response["refresh_token"]

    def test_token_test(self, authoriser: APIAuthoriser, token: dict[str, Any]):
        authoriser.token = {"expires_at": (datetime.now() + timedelta(seconds=3000)).timestamp()}
        authoriser.test_expiry = 1500
        assert authoriser.test_token()

    def test_error_test(self, authoriser: APIAuthoriser, token: dict[str, Any]):
        authoriser.token = {"error": "error message"}
        assert not authoriser._test_no_error()

        authoriser.token = token
        assert authoriser._test_no_error()

    def test_valid_response(self, authoriser: APIAuthoriser, token: dict[str, Any], requests_mock: Mocker):
        assert authoriser._test_valid_response()

        authoriser.header_key = "Authorization"
        authoriser.header_prefix = "Bearer "
        authoriser.token_key_path = ["access", "token"]
        authoriser.token = {"access": {"token": "i am a token"}} | token
        authoriser.test_args = {"url": "http://locahost/test"}
        authoriser.test_condition = lambda x: x["test_result"] == "valid"

        requests_mock.get(authoriser.test_args["url"], json={"test_result": "valid"})
        assert authoriser._test_valid_response()

        authoriser.test_condition = lambda x: x == "valid"

        requests_mock.get(authoriser.test_args["url"], text="valid")
        assert authoriser._test_valid_response()

        requests_mock.get(authoriser.test_args["url"], text="invalid")
        assert not authoriser._test_valid_response()

    def test_expiry(self, authoriser: APIAuthoriser):
        authoriser.token = {"expires_at": (datetime.now() + timedelta(seconds=3000)).timestamp()}
        authoriser.test_expiry = 1500
        assert authoriser._test_expiry()

        authoriser.test_expiry = 0
        assert authoriser._test_expiry()

        authoriser.token = {}
        authoriser.test_expiry = 2000
        assert authoriser._test_expiry()

        authoriser.token = {"expires_at": (datetime.now() + timedelta(seconds=1000)).timestamp()}
        authoriser.test_expiry = 2000
        assert not authoriser._test_expiry()

    def test_auth_new_token(self, token: dict[str, Any], token_file_path: str, requests_mock: Mocker):
        authoriser = APIAuthoriser(name="test", auth_args={"url": "http://localhost/auth"}, test_expiry=1000)

        response = {"access_token": "valid token", "expires_in": 3000, "refresh_token": "new_refresh"}
        requests_mock.post(authoriser.auth_args["url"], json=response)

        authoriser.authorise()
        expected_header = {"Authorization": f"Bearer valid token"}
        assert authoriser.headers == expected_header
        assert authoriser.token["refresh_token"] == "new_refresh"

    def test_auth_load_and_token_valid(self, token_file_path: str, requests_mock: Mocker):
        authoriser = APIAuthoriser(
            name="test",
            test_args={"url": "http://localhost/test"},
            test_condition=lambda x: x["test"] != "error",
            token_file_path=token_file_path,
        )

        requests_mock.get(authoriser.test_args["url"], json={"test": "valid"})

        # loads token, token is valid, no refresh needed
        authoriser.authorise()
        expected_header = {"Authorization": f"Bearer {authoriser.token["access_token"]}"}
        assert authoriser.headers == expected_header

    def test_auth_force_load_and_token_valid(self, token_file_path: str):
        authoriser = APIAuthoriser(
            name="test",
            token={"this token": "is not valid"},
            token_file_path=token_file_path,
            header_key="new_key",
            header_prefix="prefix - ",
            header_extra={"key": "extra value"}
        )

        # force load from json despite being given token
        authoriser.authorise(force_load=True)
        expected_header = {"new_key": f"prefix - {authoriser.token["access_token"]}"}

        assert authoriser.headers == expected_header | authoriser.header_extra

    def test_auth_force_new_and_no_args(self, token: dict[str, Any], token_file_path: str):
        authoriser = APIAuthoriser(name="test", token=token, token_file_path=token_file_path)

        # force new despite being given token and token file path
        with pytest.raises(APIError):
            authoriser.authorise(force_new=True)

    def test_auth_new_token_and_no_refresh(self, token: dict[str, Any], token_file_path: str, requests_mock: Mocker):
        authoriser = APIAuthoriser(
            name="test",
            auth_args={"url": "http://localhost/auth"},
            token_key_path=["1", "2", "code"]
        )

        requests_mock.post(authoriser.auth_args["url"], json={"1": {"2": {"code": "token"}}})

        authoriser.authorise()
        expected_header = {"Authorization": f"Bearer token"}
        assert authoriser.headers == expected_header

    def test_auth_new_token_and_refresh_valid(self, token: dict[str, Any], token_file_path: str, requests_mock: Mocker):
        authoriser = APIAuthoriser(
            name="test",
            refresh_args={"url": "http://localhost/refresh"},
            test_expiry=1000,
            token=token | {"refresh_token": "refresh me"} | {"expires_in": 10},
            token_key_path=("get_token",)
        )

        response = {"get_token": "valid token", "expires_in": 3000, "refresh_token": "new_refresh"}
        requests_mock.post(authoriser.refresh_args["url"], json=response)

        authoriser.authorise()
        expected_header = {"Authorization": f"Bearer valid token"}
        assert authoriser.headers == expected_header
        assert authoriser.token["refresh_token"] == "new_refresh"

    def test_auth_new_token_and_refresh_invalid(
            self, token: dict[str, Any], token_file_path: str, requests_mock: Mocker
    ):
        authoriser = APIAuthoriser(
            name="test",
            refresh_args={"url": "http://localhost/refresh"},
            test_expiry=1000,
            token=token | {"refresh_token": "refresh me"} | {"expires_in": 10},
            token_key_path=("get_token",)
        )

        response = {"expires_in": 10}
        requests_mock.post(authoriser.refresh_args["url"], json=response)

        with pytest.raises(APIError):
            authoriser.authorise()

        authoriser.auth_args = {"url": "http://localhost/auth"}
        response = {"get_token": "valid token", "expires_in": 20, "refresh_token": "new_refresh"}
        requests_mock.post(authoriser.auth_args["url"], json=response)

        with pytest.raises(APIError):
            authoriser.authorise()

        response = {"get_token": "valid token", "expires_in": 3000, "refresh_token": "new_refresh"}
        requests_mock.post(authoriser.auth_args["url"], json=response)

        authoriser.authorise()
        expected_header = {"Authorization": f"Bearer valid token"}
        assert authoriser.headers == expected_header
        assert authoriser.token["refresh_token"] == "new_refresh"
