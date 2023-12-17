from typing import Any

from syncify import PROGRAM_NAME
from syncify.spotify import URL_API, URL_AUTH
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from ._core import SpotifyAPICore
from ._item import SpotifyAPIItems
from ._playlist import SpotifyAPIPlaylists

# non-user authenticated access
API_AUTH_BASIC = {
    "auth_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "client_credentials",
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "user_args": None,
    "refresh_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}

# user authenticated access with scopes
API_AUTH_USER = {
    "auth_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "authorization_code",
            "code": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "user_args": {
        "url": f"{URL_AUTH}/authorize",
        "params": {
            "response_type": "code",
            "client_id": "{client_id}",
            "scope": " ".join(
                [
                    "playlist-modify-public",
                    "playlist-modify-private",
                    "playlist-read-collaborative",
                ]
            ),
            "state": PROGRAM_NAME,
        },
    },
    "refresh_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_args": {"url": f"{URL_API}/me"},
    "test_condition": lambda r: "href" in r and "display_name" in r,
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}


# noinspection PyShadowingNames
class SpotifyAPI(SpotifyDataWrangler, SpotifyAPICore, SpotifyAPIItems, SpotifyAPIPlaylists):
    """
    Collection of endpoints for the Spotify API.
    See :py:class:`RequestHandler` and :py:class:`APIAuthoriser`
    for more info on which params to pass to authorise and execute requests.

    :param handler_kwargs: The authorisation kwargs to be passed to :py:class:`RequestHandler`.
    """

    @property
    def api_url_base(self) -> str:
        return URL_API

    @property
    def user_id(self) -> str | None:
        """ID of the currently authenticated user"""
        if not self._user_data:
            self._user_data = self.get_self()
        return self._user_data["id"]

    @property
    def user_name(self) -> str | None:
        """Name of the currently authenticated user"""
        if not self._user_data:
            self._user_data = self.get_self()
        return self._user_data["display_name"]

    def __init__(self, **handler_kwargs):
        super().__init__(**handler_kwargs)
        self._user_data: dict[str, Any] = {}
