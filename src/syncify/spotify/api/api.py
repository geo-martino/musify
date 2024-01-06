import base64
from collections.abc import Iterable
from copy import deepcopy

from syncify import PROGRAM_NAME
from syncify.spotify import URL_API, URL_AUTH
from syncify.spotify.api.misc import SpotifyAPIMisc
from syncify.spotify.api.item import SpotifyAPIItems
from syncify.spotify.api.playlist import SpotifyAPIPlaylists
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from syncify.shared.utils import safe_format_map

# user authenticated access with scopes
SPOTIFY_API_AUTH_ARGS = {
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
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}


class SpotifyAPI(SpotifyAPIMisc, SpotifyAPIItems, SpotifyAPIPlaylists, SpotifyDataWrangler):
    """
    Collection of endpoints for the Spotify API.
    See :py:class:`RequestHandler` for more info on optional params to pass as ``**kwargs``.

    :param client_id: The client ID to use when authorising requests.
    :param client_secret: The client secret to use when authorising requests.
    :param scopes: The scopes to request access to.
    """

    items_key = "items"

    @property
    def api_url_base(self) -> str:
        return URL_API

    @property
    def user_id(self) -> str | None:
        """ID of the currently authenticated user"""
        if not self.user_data:
            self.user_data = self.get_self()
        return self.user_data["id"]

    @property
    def user_name(self) -> str | None:
        """Name of the currently authenticated user"""
        if not self.user_data:
            self.user_data = self.get_self()
        return self.user_data["display_name"]

    def __init__(
            self,
            client_id: str | None = None,
            client_secret: str | None = None,
            scopes: Iterable[str] = (),
            **kwargs,
    ):
        format_map = {
            "client_id": client_id,
            "client_base64": base64.b64encode(f"{client_id}:{client_secret}".encode()).decode(),
            "scopes": " ".join(scopes),
        }
        auth_kwargs = deepcopy(SPOTIFY_API_AUTH_ARGS)
        safe_format_map(auth_kwargs, format_map=format_map)

        super().__init__(**auth_kwargs, **kwargs)


if __name__ == "__main__":
    import os

    api = SpotifyAPI(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        scopes=[
            "user-library-read",
            "user-follow-read",
            "playlist-modify-public",
            "playlist-modify-private",
            "playlist-read-collaborative",
            "playlist-read-private"
        ],
        token_file_path="_data/token.json",
    )
    api.authorise(force_new=False)

    print(api.get_self())