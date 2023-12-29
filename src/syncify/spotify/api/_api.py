import os

from syncify import PROGRAM_NAME
from syncify.spotify import URL_API, URL_AUTH
from syncify.spotify.api._core import SpotifyAPICore
from syncify.spotify.api._item import SpotifyAPIItems
from syncify.spotify.api._playlist import SpotifyAPIPlaylists
from syncify.spotify.processors.wrangle import SpotifyDataWrangler

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
        },
        "headers": {
            "content-type": "application/x-www-form-urlencoded",
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
            "redirect_uri": None,
        },
        "headers": {
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {client_base64}"
        },
    },
    "user_args": {
        "url": f"{URL_AUTH}/authorize",
        "params": {
            "client_id": "{client_id}",
            "response_type": "code",
            "redirect_uri": None,
            "state": PROGRAM_NAME,
            "scope": "{scopes}",
            "show_dialog": False,
        },
    },
    "refresh_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
        },
        "headers": {
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {client_base64}"
        },
    },
    "test_args": {"url": f"{URL_API}/me"},
    "test_condition": lambda r: "href" in r and "display_name" in r,
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}


class SpotifyAPI(SpotifyDataWrangler, SpotifyAPICore, SpotifyAPIItems, SpotifyAPIPlaylists):
    """
    Collection of endpoints for the Spotify API.
    See :py:class:`RequestHandler` and :py:class:`APIAuthoriser`
    for more info on which params to pass to authorise and execute requests.
    """

    items_key = "items"

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


if __name__ == "__main__":
    import base64
    # noinspection PyUnresolvedReferences
    import json

    # noinspection PyUnresolvedReferences
    from syncify.remote.enums import RemoteObjectType as ObjectType
    from syncify.utils.helpers import safe_format_map

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    format_map = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_base64": base64.b64encode(f"{client_id}:{client_secret}".encode()).decode(),
        "token_file_path": "_data/token.json",
        "scopes": " ".join([
            "user-library-read",
            "user-follow-read",
            "playlist-modify-public",
            "playlist-modify-private",
            "playlist-read-collaborative",
            "playlist-read-private"
        ]),
    }
    safe_format_map(API_AUTH_USER, format_map=format_map)

    api = SpotifyAPI(**API_AUTH_USER, cache_path=None)
    api.authorise(force_new=False)

    print(api.get_self())
