import json
import os
from collections.abc import Callable
from datetime import datetime as dt
from urllib.parse import urlparse
from webbrowser import open as webopen

import pytz
import requests

BASE_AUTH = "https://accounts.spotify.com"

AUTH_ARGS_BASIC = {
    "auth_args": {
        "url": f"{BASE_AUTH}/api/token",
        "data": {
            "grant_type": "client_credentials",
            "client_id": os.environ.get("CLIENT_ID"),
            "client_secret": os.environ.get("CLIENT_SECRET"),
        },
    },
    "user_args": None,
    "refresh_args": {
        "url": f"{BASE_AUTH}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": os.environ.get("CLIENT_ID"),
            "client_secret": os.environ.get("CLIENT_SECRET"),
        },
    },
    "test_expiry": 600,
    "token_path": "token.json",
    "extra_headers": {"Accept": "application/json", "Content-Type": "application/json"},
}

AUTH_ARGS_USER = {
    "auth_args": {
        "url": f"{BASE_AUTH}/api/token",
        "data": {
            "grant_type": "authorization_code",
            "code": None,
            "client_id": os.environ.get("CLIENT_ID"),
            "client_secret": os.environ.get("CLIENT_SECRET"),
            "redirect_uri": "http://localhost/",
        },
    },
    "user_args": {
        "url": f"{BASE_AUTH}/authorize",
        "params": {
            "response_type": "code",
            "client_id": os.environ.get("CLIENT_ID"),
            "scope": " ".join(
                [
                    "playlist-modify-public",
                    "playlist-modify-private",
                    "playlist-read-collaborative",
                ]
            ),
            "redirect_uri": "http://localhost/",
            "state": "syncify",
        },
    },
    "refresh_args": {
        "url": f"{BASE_AUTH}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": os.environ.get("CLIENT_ID"),
            "client_secret": os.environ.get("CLIENT_SECRET"),
        },
    },
    "test_expiry": 600,
    "token_path": "token.json",
    "extra_headers": {"Accept": "application/json", "Content-Type": "application/json"},
}


class ApiAuthoriser:
    """
    Authorises and validates an API token for given input parameters.
    Functions for returning formatted headers for future, authorised requests.
    :param auth_args: The parameters to be passed to the requests.post() function
        for initial token authorisation.
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
    :type auth_args: dict
    :param refresh_args: Parameters to be passed to the requests.post() function
        for refreshing an expired token when a refresh_token is present.
        See auth_args doc string for example value.
    :type refresh_args: dict (default value: None).
    :param test_args: Parameters to be passed to the requests.get() function
        for testing validity of the token.
        Must be set in conjunction with test_condition to work.
        See auth_args doc string for example value.
    :type test_args: dict (default value: None).
    :param test_condition: Callable function for testing the response from the given
        test_args. e.g. lambda r: "error" not in r
    :type test_condition: Callable[[dict], bool] (default value: None).
    :param test_expiry: Time in seconds left until the token is due to expire.
    :type test_expiry: int (default value: None).
    :param token: Define a custom input token for initialisation.
    :type token: dict (default value: None).
    :param token_path: Path to use for loading and saving a token.
    :type token_path: str (default value: None).
    :param extra_headers: Extra data to add to the final headers for future
        successful requests.
    :type extra_headers: dict (default value: None).
    """

    def __init__(
        self,
        auth_args: dict,
        user_args: dict,
        refresh_args: dict = None,
        test_args: dict = None,
        test_condition: Callable = None,
        test_expiry: int = None,
        token: dict = None,
        token_path: str = "/tmp/token.json",
        extra_headers: dict = None,
    ):
        # dictionaries of requests parameters to be parsed to requests
        self._auth_args = auth_args
        self._user_args = user_args
        self._refresh_args = refresh_args

        # test params and conditions
        self._test_args = test_args
        self._test_condition = test_condition
        self._test_expiry = test_expiry

        # store token
        if not token_path.lower().endswith(".json"):
            token_path += ".json"
        self._token = token
        self._token_path = token_path

        # extra information to add to the final headers
        self._extra_headers = extra_headers

    def auth(self, force_new: bool = False, force_load: bool = False) -> dict:
        """
        Main method for authentication, tests/refreshes/reauthorises as needed

        :param force_new: bool, default=False. Ignore saved/loaded token and generate new token.
        :param force_load: bool, default=False. Forces loading of new token even if force_new is True.
        :return: dict. Headers for requests authorisation.
        """
        # attempt to load stored token if found
        if (self._token is None or force_load) and not force_new:
            self.load_token()

        # generate new token if not or force is enabled
        if self._token is None:
            self._logger.debug("Saved access token not found. Generating new token...")
            self.request_token(self._auth_args, user_args=self._user_args)
        elif force_new:
            self._logger.debug("New token generation forced. Generating new token...")
            self.request_token(self._auth_args, user_args=self._user_args)

        # test current token
        valid = self.test_token()
        refreshed = False

        # if invalid, first attempt to re-authorise via refresh_token
        if (
            not valid
            and "refresh_token" in self._token
            and self._refresh_args is not None
        ):
            self._logger.debug(
                "Access token is not valid and refresh data found. "
                "Refreshing token and testing...")

            self._refresh_args["data"]["refresh_token"] = self._token["refresh_token"]
            self.request_token(self._refresh_args, user_args=None)
            valid = self.test_token()
            refreshed = True

        if not valid:  # generate new token
            if refreshed:
                self._logger.debug(
                    "Refreshed access token is still not valid. Generating new token..."
                )
            else:
                self._logger.debug(
                    "Access token is not valid and and no refresh data found."
                    "Generating new token..."
                )

            self.request_token(self._auth_args, user_args=self._user_args)
            valid = self.test_token()
            if not valid:
                self._logger.critical(json.dumps(self.format_token(), indent=2))
                raise Exception("Token is still not valid.")

        self._logger.debug("Access token is valid. Saving...")
        self.save_token()
        self._logger.info("\33[92mAuthorisation done. \33[0m")

        return self.get_headers()

    def test_token(self) -> bool:
        """Test validity of token and given headers"""
        self._logger.debug("Begin testing token...")
        headers = self.get_headers()
        not_expired = True
        valid_response = True

        # test for has not expired
        if "expires_at" in self._token and self._test_expiry is not None:
            now = pytz.timezone("UTC").localize(dt.now()).timestamp()
            not_expired = (now + self._test_expiry) < self._token["expires_at"]
            self._logger.debug(f"Expiry time test: {not_expired}")

        # test for expected response
        if self._test_args is not None and self._test_condition is not None:
            self._test_args["headers"] = headers

            response = requests.get(**self._test_args)
            try:
                response = response.json()
            except json.JSONDecodeError:
                response = response.text

            valid_response = self._test_condition(response)
            self._logger.debug(f"Valid response test: {valid_response}")

        return not_expired and valid_response

    def request_token(self, requests_args: dict, user_args: dict) -> dict:
        """
        Authenticates/refreshes basic API access and returns token.

        :param requests_args: dict. Authorisation data to post via requests.
        """
        if user_args:  # TODO: Flask server for picking up redirects for token code instead?
            self._logger.info("Authorising user privilege access...")

            # opens in user's browser to authenticate
            # user must wait for redirect and input the given link
            webopen(requests.post(**user_args).url)
            print("\33[1m\nLog in to Spotify in your browser, authorise, and type in the url once the page fails to load\33[0m")
            redirect_url = input("URL: ")

            # format out the access code from the returned url
            code = urlparse(redirect_url).query.split("&")[0].split("=")[1]

            # modify requests args for authorization_code based auth
            requests_args["data"]["code"] = code

        # post auth request
        auth_response = requests.post(**requests_args).json()

        # add granted and expiry time information to token
        now = pytz.timezone("UTC").localize(dt.now()).timestamp()
        auth_response["granted_at"] = now
        if "expires_in" in auth_response:
            expires_at = auth_response["granted_at"] + float(
                auth_response["expires_in"]
            )
            auth_response["expires_at"] = expires_at

        # request sometimes returns new refresh token, append previous one if not
        if "refresh_token" not in auth_response:
            if self._token is not None and "refresh_token" in self._token:
                auth_response["refresh_token"] = self._token["refresh_token"]

        self._logger.debug("New token successfully generated.")
        self._token = auth_response
        return self._token

    def get_headers(self) -> dict:
        """Format headers to usage appropriate format"""
        token_type = self._token.get("token_type", "Bearer")
        headers = {"Authorization": f"{token_type} {self._token.get('access_token')}"}

        if isinstance(self._extra_headers, dict):
            headers.update(self._extra_headers)

        return headers

    #############################################################
    ## JSON I/O functions
    #############################################################
    def load_token(self) -> dict:
        """Load stored token from given path"""
        if os.path.exists(self._token_path):
            self._logger.debug("Saved access token found. Loading stored token...")
            try:
                with open(self._token_path, "r") as file:  # load token
                    self._token = json.load(file)
            except json.decoder.JSONDecodeError:
                self._logger.debug("Failed to load token. JSON decoder error.")

        return self._token

    def save_token(self) -> None:
        """Save new/updated token to given path"""
        self._logger.debug(f"Saving token: \n{json.dumps(self.format_token(), indent=2)}")
        with open(self._token_path, "w") as file:
            json.dump(self._token, file, indent=2)

    def format_token(self) -> dict:
        token = self._token.copy()
        if "granted_at" in token:
            token["granted_at"] = dt.utcfromtimestamp(token["granted_at"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        if "expires_at" in token:
            token["expires_at"] = dt.utcfromtimestamp(token["expires_at"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return token
