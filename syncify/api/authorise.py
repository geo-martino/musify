import json
import os
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM
from typing import Any
from urllib.parse import urlparse, parse_qs
from webbrowser import open as webopen

import requests

from syncify import PROGRAM_NAME
from syncify.api.exception import APIError
from syncify.utils.logger import Logger


class APIAuthoriser(Logger):
    """
    Authorises and validates an API token for given input parameters.
    Functions for returning formatted headers for future, authorised requests.

    :param name: The name of the service being accessed.
    :param auth_args: The parameters to be passed to the requests.post() function for initial token authorisation.
        e.g.    {
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
    :param user_args: Parameters to be passed to the requests.post() function
        for requesting user authenticated access to API services.
        The code response from this request is then added to the authentication request args
        to grant user authorisation to the API.
        See ``auth_args`` for possible example values.
    :param refresh_args: Parameters to be passed to the requests.post() function
        for refreshing an expired token when a refresh_token is present.
        See ``auth_args`` for possible example values.
    :param test_args: Parameters to be passed to the requests.get() function for testing validity of the token.
        Must be set in conjunction with test_condition to work.
        See auth_args doc string for possible example values.
    :param test_condition: Callable function for testing the response from the given
        test_args. e.g. lambda r: "error" not in r
    :param test_expiry: The time allowance in seconds left until the token is due to expire to use when testing.
        Useful at ensuring the token will be valid for long enough to run your operations.
        e.g. if a token has 600 second total expiry time,
            it is 60 seconds old and therefore still had 540 seconds of authorised time left,
            and you set ``test_expiry``=300, the token will pass tests.
            However, if the same token is tested again later when it is 500 seconds old
            and has only 100 seconds of authorised time left,
            it will now fail the tests and will need to be refreshed.
    :param token: Define a custom input token for initialisation.
    :param token_file_path: Path to use for loading and saving a token.
    :param token_key_path: Keys to the token in auth response. Looks for key 'access_token' by default.
    :param header_key: Header key to apply to headers for authenticated calls to the API.
    :param header_prefix: Prefix to add to the header value for authenticated calls to the API.
    :param header_extra: Extra data to add to the final headers for future successful requests.
    """

    @property
    def token_safe(self) -> dict[str, Any]:
        """Returns a reformatted token, making it safe to log by removing sensitive values at predefined keys."""
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
        auth_args: Mapping[str, Any],
        user_args: Mapping[str, Any] | None = None,
        refresh_args: Mapping[str, Any] | None = None,
        test_args: Mapping[str, Any] | None = None,
        test_condition: Callable[[str | Mapping[str, Any]], bool] | None = None,
        test_expiry: int = 0,
        token: Mapping[str, Any] | None = None,
        token_file_path: str | None = None,
        token_key_path: Sequence[str] = (),
        header_key: str = "Authorization",
        header_prefix: str | None = "Bearer ",
        header_extra: Mapping[str, str] | None = None,
    ):
        Logger.__init__(self)
        self.name = name

        # maps of requests parameters to be passed to `requests` functions
        self.auth_args: Mapping[str, Any] = auth_args
        self.user_args: Mapping[str, Any] | None = user_args
        self.refresh_args: Mapping[str, Any] | None = refresh_args

        # test params and conditions
        self.test_args: Mapping[str, Any] | None = test_args
        self.test_condition: Callable[[str | Mapping[str, Any]], bool] | None = test_condition
        self.test_expiry: int = test_expiry

        # store token
        self.token: Mapping[str, Any] | None = token
        self.token_file_path: str | None = token_file_path
        self.token_key_path: Sequence[str] = token_key_path if token_key_path else ("access_token",)

        # information for the final headers
        self.header_key: str = header_key
        self.header_prefix: str = header_prefix if header_prefix else ""
        self.header_extra: Mapping[str, str] = header_extra if header_extra else {}

    def auth(self, force_load: bool = False, force_new=False) -> dict[str, str]:
        """
        Main method for authentication, tests/refreshes/reauthorises as needed

        :param force_load: Reloads the token even if it's already been loaded into the object.
            Ignored when force_new is True.
        :param force_new: Ignore saved/loaded token and generate new token.
        :return: Headers for request authorisation.
        :raise APIError: If the token cannot be validated.
        """
        # attempt to load stored token if found
        if (self.token is None or force_load) and not force_new:
            self.load_token()

        # generate new token if not or force is enabled
        if self.token is None:
            self.logger.debug("Saved access token not found. Generating new token...")
            self._request_token(user=True, **self.auth_args)
        elif force_new:
            self.logger.debug("New token generation forced. Generating new token...")
            self._request_token(user=True, **self.auth_args)

        # test current token
        valid = self.test()
        refreshed = False

        # if invalid, first attempt to re-authorise via refresh_token
        if not valid and "refresh_token" in self.token and self.refresh_args is not None:
            self.logger.debug("Access token is not valid and refresh data found. Refreshing token and testing...")

            self.refresh_args["data"]["refresh_token"] = self.token["refresh_token"]
            self._request_token(user=False, **self.refresh_args)
            valid = self.test()
            refreshed = True

        if not valid:  # generate new token
            if refreshed:
                self.logger.debug("Refreshed access token is still not valid. Generating new token...")
            else:
                self.logger.debug("Access token is not valid and and no refresh data found. Generating new token...")

            self._request_token(user=True, **self.auth_args)
            valid = self.test()
            if not valid:
                raise APIError(f"Token is still not valid: {self.token_safe}")

        self.logger.debug("Access token is valid. Saving...")
        self.save_token()

        return self.headers

    def _auth_user(self, **requests_args) -> None:
        """
        Add user authentication code to request args by authorising through user's browser

        :param requests_args: requests.post() parameters to enrich.
        """
        if not self.user_args:
            return

        self.logger.info_extra("Authorising user privilege access...")

        # set up socket to listen for the redirect from
        address = ("localhost", 8080)
        code_listener = socket(AF_INET, SOCK_STREAM)
        code_listener.bind(address)
        code_listener.settimeout(120)
        code_listener.listen(1)

        print(
            f"\33[1mOpening {self.name} in your browser. "
            f"Log in to {self.name}, authorise, and return here after \33[0m"
        )
        print(f"\33[1mWaiting for code, timeout in {code_listener.timeout} seconds... \33[0m")

        # open authorise webpage and wait for the redirect
        self.user_args["params"]["redirect_uri"] = f"http://{address[0]}:{address[1]}/"
        webopen(requests.post(**self.user_args).url)
        request, _ = code_listener.accept()

        request.send(
            f"Code received! You may now close this window and return to {PROGRAM_NAME}...".encode("utf-8")
        )
        print("\33[92;1mCode received! \33[0m")
        code_listener.close()

        # format out the access code from the returned response
        path_raw = next(line for line in request.recv(8196).decode("utf-8").split('\n') if line.startswith("GET"))
        requests_args["data"]["code"] = parse_qs(urlparse(path_raw).query)["code"][0]

    def _request_token(self, user: bool = True, **requests_args) -> None:
        """
        Authenticates/refreshes basic API access and returns token.

        :param user: Authenticate as the user first to user to generate a user access authenticated token.
        :param requests_args: requests.post() parameters to send as a request for authorisation.
        """
        if user and self.user_args and not requests_args["data"].get("code"):
            self._auth_user(**requests_args)

        # post auth request
        auth_response = requests.post(**requests_args).json()

        # add granted and expiry time information to token
        auth_response["granted_at"] = datetime.now().timestamp()
        if "expires_in" in auth_response:
            expires_at = auth_response["granted_at"] + float(auth_response["expires_in"])
            auth_response["expires_at"] = expires_at

        # request sometimes returns new refresh token, append previous one if not
        if "refresh_token" not in auth_response:
            if self.token is not None and "refresh_token" in self.token:
                auth_response["refresh_token"] = self.token["refresh_token"]

        self.logger.debug("New token successfully generated.")
        self.token = auth_response

    def test(self) -> bool:
        """Test validity of token and given headers. Returns True if all tests pass, False otherwise"""
        self.logger.debug("Begin testing token...")

        not_expired = True
        valid_response = True

        token_has_no_error = "error" not in self.token
        self.logger.debug(f"Token contains no error test: {token_has_no_error}")
        if not token_has_no_error:
            return False

        # test for expected response
        if self.test_args is not None and self.test_condition is not None:
            response = requests.get(headers=self.headers, **self.test_args)
            try:
                response = response.json()
            except json.JSONDecodeError:
                response = response.text

            valid_response = self.test_condition(response)
            self.logger.debug(f"Valid response test: {valid_response}")

        # test for has not expired
        if "expires_at" in self.token and self.test_expiry > 0:
            not_expired = datetime.now().timestamp() + self.test_expiry < self.token["expires_at"]
            self.logger.debug(f"Expiry time test: {not_expired}")

        return all([token_has_no_error, valid_response, not_expired])

    def load_token(self) -> dict[str, Any]:
        """Load stored token from given path"""
        if self.token_file_path and os.path.exists(self.token_file_path):
            self.logger.debug("Saved access token found. Loading stored token...")
            with open(self.token_file_path, "r") as file:  # load token
                self.token = json.load(file)

        return self.token

    def save_token(self) -> None:
        """Save new/updated token to given path"""
        self.logger.debug(f"Saving token: {self.token_safe}")
        with open(self.token_file_path, "w") as file:
            json.dump(self.token, file, indent=2)
