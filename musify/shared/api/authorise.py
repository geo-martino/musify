"""
Handle API authorisation for requesting access tokens to an API.
"""

import json
import logging
import os
import socket
from collections.abc import Callable, Mapping, Sequence, MutableMapping
from datetime import datetime
from typing import Any
from urllib.parse import urlparse, parse_qs
from webbrowser import open as webopen

import requests

from musify import PROGRAM_NAME
from musify.shared.api.exception import APIError
from musify.shared.logger import MusifyLogger


class APIAuthoriser:
    """
    Authorises and validates an API token for given input parameters.
    Functions for returning formatted headers for future, authorised requests.

    Any ``..._args`` parameters must be provided as a dictionary of parameters to be passed directly
    to the :py:class:`requests` module e.g.

    .. code-block:: python

        user_args = {
            "url": token_url,
            "params": {},
            "data": {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            "auth": ('user', 'pass'),
            "headers": {},
            "json": {},
        }

    :param name: The name of the API service being accessed.
    :param auth_args: The parameters to be passed to the requests.post() function for initial token authorisation.
        See description for possible example values.
    :param user_args: Parameters to be passed to the requests.post() function
        for requesting user authorised access to API services.
        The code response from this request is then added to the authorisation request args
        to grant user authorisation to the API.
        See description for possible example values.
    :param refresh_args: Parameters to be passed to the requests.post() function
        for refreshing an expired token when a refresh_token is present.
        See description for possible example values.
    :param test_args: Parameters to be passed to the requests.get() function for testing validity of the token.
        Must be set in conjunction with test_condition to work.
        See description for possible example values.
    :param test_condition: Callable function for testing the response from the given
        test_args. e.g. ``lambda r: "error" not in r``
    :param test_expiry: The time allowance in seconds left until the token is due to expire to use when testing.
        Useful for ensuring the token will be valid for long enough to run your operations e.g.

        - a token has 600 second total expiry time,
        - it is 60 seconds old and therefore still has 540 seconds of authorised time left,
        - you set ``test_expiry`` = 300, the token will pass tests.
        - the same token is tested again later when it is 500 seconds old,
        - it now has only 100 seconds of authorised time left,
        - it will now fail the tests as 100 < 300 and will need to be refreshed.
    :param token: Define a custom input token for initialisation.
    :param token_file_path: Path to use for loading and saving a token.
    :param token_key_path: Keys to the token in auth response. Looks for key 'access_token' by default.
    :param header_key: Header key to apply to headers for authorised calls to the API.
    :param header_prefix: Prefix to add to the header value for authorised calls to the API.
    :param header_extra: Extra data to add to the final headers for future successful requests.
    """

    __slots__ = (
        "logger",
        "name",
        "auth_args",
        "user_args",
        "refresh_args",
        "test_args",
        "test_condition",
        "test_expiry",
        "token",
        "token_file_path",
        "token_key_path",
        "header_key",
        "header_prefix",
        "header_extra",
    )

    _user_auth_socket_address = "localhost"
    _user_auth_socket_port = 8080

    @property
    def token_safe(self) -> dict[str, Any]:
        """Returns a reformatted token, making it safe to log by removing sensitive values at predefined keys."""
        if not self.token:
            return {}
        return {k: f"{v[:5]}..." if str(k).endswith("_token") else v for k, v in self.token.items()}

    @property
    def headers(self) -> dict[str, str]:
        """
        Format headers to usage appropriate format

        :raise APIError: If no token has been loaded,
            or a valid value was not found at the ``token_key_path`` within the token
        """
        if self.token is None:
            raise APIError("Token not loaded.")

        token_value = self.token
        for key in self.token_key_path:  # get token key value at given path
            token_value = token_value.get(key, {})

        if not isinstance(token_value, str):
            raise APIError(
                f"Did not find valid token at key path: {self.token_key_path} -> {token_value} | " +
                str(self.token_safe)
            )

        return {self.header_key: f"{self.header_prefix}{token_value}"} | self.header_extra

    def __init__(
        self,
        name: str,
        auth_args: MutableMapping[str, Any] | None = None,
        user_args: Mapping[str, Any] | None = None,
        refresh_args: Mapping[str, Any] | None = None,
        test_args: Mapping[str, Any] | None = None,
        test_condition: Callable[[str | Mapping[str, Any]], bool] | None = None,
        test_expiry: int = 0,
        token: Mapping[str, Any] | None = None,
        token_file_path: str | None = None,
        token_key_path: Sequence[str] = ("access_token",),
        header_key: str = "Authorization",
        header_prefix: str | None = "Bearer ",
        header_extra: Mapping[str, str] | None = None,
    ):
        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)
        self.name = name

        # maps of requests parameters to be passed to `requests` functions
        self.auth_args: MutableMapping[str, Any] | None = auth_args
        self.user_args: dict[str, Any] | None = user_args
        self.refresh_args: dict[str, Any] | None = refresh_args

        # test params and conditions
        self.test_args: Mapping[str, Any] | None = test_args
        self.test_condition: Callable[[str | Mapping[str, Any]], bool] | None = test_condition
        self.test_expiry: int = test_expiry

        # store token
        self.token: Mapping[str, Any] | None = token
        self.token_file_path: str | None = token_file_path
        self.token_key_path: Sequence[str] = token_key_path

        # information for the final headers
        self.header_key: str = header_key
        self.header_prefix: str = header_prefix or ""
        self.header_extra: dict[str, str] = header_extra or {}

    def load_token(self) -> dict[str, Any] | None:
        """Load stored token from given path"""
        if not self.token_file_path or not os.path.exists(self.token_file_path):
            return self.token

        self.logger.debug("Saved access token found. Loading stored token...")
        with open(self.token_file_path, "r") as file:  # load token
            self.token = json.load(file)
        return self.token

    def save_token(self) -> None:
        """Save new/updated token to given path"""
        if not self.token_file_path or not self.token:
            return

        self.logger.debug(f"Saving token: {self.token_safe}")
        with open(self.token_file_path, "w") as file:
            json.dump(self.token, file, indent=2)

    def authorise(self, force_load: bool = False, force_new: bool = False) -> dict[str, str]:
        """
        Main method for authorisation which tests/refreshes/reauthorises as needed.

        :param force_load: Reloads the token even if it's already been loaded into the object.
            Ignored when force_new is True.
        :param force_new: Ignore saved/loaded token and generate new token.
        :return: Headers for request authorisation.
        :raise APIError: If the token cannot be validated.
        """
        # attempt to load stored token if found
        if force_new:
            self.token = None
        elif self.token is None or force_load:
            self.load_token()

        # generate new token if not or force is enabled
        if self.auth_args and self.token is None:
            log = "Saved access token not found" if self.token is None else "New token generation forced"
            self.logger.debug(f"{log}. Generating new token...")
            self._authorise_user()
            self._request_token(**self.auth_args)

        # test current token
        valid = self.test_token()
        refreshed = False

        # if invalid, first attempt to re-authorise via refresh_token
        if not valid and self.token and "refresh_token" in self.token and self.refresh_args is not None:
            self.logger.debug("Access token is not valid and refresh data found. Refreshing token and testing...")

            if "data" not in self.refresh_args:
                self.refresh_args["data"] = {}
            self.refresh_args["data"]["refresh_token"] = self.token["refresh_token"]
            self._request_token(**self.refresh_args)

            valid = self.test_token()
            refreshed = True

        if not valid and self.auth_args:  # generate new token
            if refreshed:
                log = "Refreshed access token is still not valid"
            else:
                log = "Access token is not valid and and no refresh data found"
            self.logger.debug(f"{log}. Generating new token...")

            self._authorise_user()
            self._request_token(**self.auth_args)
            valid = self.test_token()

        if not self.token:
            raise APIError("Token not generated")
        elif not valid:
            raise APIError(f"Token is still not valid: {self.token_safe}")

        self.logger.debug("Access token is valid. Saving...")
        self.save_token()

        return self.headers

    def _authorise_user(self) -> None:
        """
        Get user authentication code by authorising through user's browser.

        :return: The authentication code
        """
        if not self.user_args or (self.auth_args and self.auth_args.get("data", {}).get("code")):
            return

        self.logger.info_extra("Authorising user privilege access...")

        # set up socket to listen for the redirect from
        socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_listener.bind((self._user_auth_socket_address, self._user_auth_socket_port))
        socket_listener.settimeout(120)
        socket_listener.listen(1)

        print(
            f"\33[1mOpening {self.name} in your browser. "
            f"Log in to {self.name}, authorise, and return here after \33[0m"
        )
        print(f"\33[1mWaiting for code, timeout in {socket_listener.timeout} seconds... \33[0m")

        # add redirect URI to auth_args and user_args
        if not self.auth_args.get("data"):
            self.auth_args["data"] = {}
        if not self.user_args.get("params"):
            self.user_args["params"] = {}
        redirect_uri = f"http://{self._user_auth_socket_address}:{self._user_auth_socket_port}/"
        self.auth_args["data"]["redirect_uri"] = redirect_uri
        self.user_args["params"]["redirect_uri"] = redirect_uri

        # open authorise webpage and wait for the redirect
        auth_response = requests.post(**self.user_args)
        webopen(auth_response.url)
        request, _ = socket_listener.accept()

        request.send(f"Code received! You may now close this window and return to {PROGRAM_NAME}...".encode("utf-8"))
        print("\33[92;1mCode received!\33[0m")
        socket_listener.close()

        # format out the access code from the returned response
        path_raw = next(line for line in request.recv(8196).decode("utf-8").split('\n') if line.startswith("GET"))
        code = parse_qs(urlparse(path_raw).query)["code"][0]

        if "data" not in self.auth_args:
            self.auth_args["data"] = {}
        self.auth_args["data"]["code"] = code

    def _request_token(self, **requests_args) -> dict[str, Any]:
        """
        Authenticates/refreshes basic API access and returns token.

        :param user: Authenticate as the user first to user to generate a user access authenticated token.
        :param data: requests.post() ``data`` parameter to send as a request for authorisation.
        :param requests_args: Other requests.post() parameters to send as a request for authorisation.
        """
        auth_response = requests.post(**requests_args).json()

        # add granted and expiry times to token
        auth_response["granted_at"] = datetime.now().timestamp()
        if "expires_in" in auth_response:
            expires_at = auth_response["granted_at"] + float(auth_response["expires_in"])
            auth_response["expires_at"] = expires_at

        # request sometimes returns new refresh token, append previous one if not
        if "refresh_token" not in auth_response:
            if self.token is not None and "refresh_token" in self.token:
                auth_response["refresh_token"] = self.token["refresh_token"]

        self.token = auth_response
        self.logger.debug(f"New token successfully generated: {self.token_safe}")
        return auth_response

    def test_token(self) -> bool:
        """Test validity of token and given headers. Returns True if all tests pass, False otherwise"""
        if not self.token:
            return False

        self.logger.debug("Begin testing token...")

        token_has_no_error = self._test_no_error()
        if not token_has_no_error:  # skip other tests if error
            return False

        valid_response = self._test_valid_response()
        not_expired = self._test_expiry()

        return token_has_no_error and valid_response and not_expired

    def _test_no_error(self) -> bool:
        """Check if the token contains an error message"""
        result = "error" not in self.token
        self.logger.debug(f"Token contains no error test: {result}")
        return result

    def _test_valid_response(self) -> bool:
        """Check for expected response"""
        if self.test_args is None or self.test_condition is None:
            return True

        response = requests.get(headers=self.headers, **self.test_args)
        try:
            response = response.json()
        except json.JSONDecodeError:
            response = response.text

        result = self.test_condition(response)
        self.logger.debug(f"Valid response test: {result}")
        return result if result is not None else False

    def _test_expiry(self) -> bool:
        """Check if the token is within accepted time range for expiry"""
        if all(key not in self.token for key in ("expires_at", "expires_in")) or self.test_expiry <= 0:
            return True

        if "expires_at" in self.token:
            result = datetime.now().timestamp() + self.test_expiry < self.token["expires_at"]
        else:
            result = self.test_expiry < self.token["expires_in"]

        self.logger.debug(f"Expiry time test: {result}")
        return result
