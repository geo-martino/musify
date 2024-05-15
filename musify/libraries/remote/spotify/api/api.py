"""
Mixin for all implementations of :py:class:`RemoteAPI` for the Spotify API.

Also includes the default arguments to be used when requesting authorisation from the Spotify API.
"""
import base64
from collections.abc import Iterable
from copy import deepcopy

from musify import PROGRAM_NAME
from musify.api.authorise import APIAuthoriser
from musify.api.cache.backend.base import ResponseCache
from musify.api.exception import APIError
from musify.libraries.remote.spotify.api.cache import SpotifyRequestSettings, SpotifyPaginatedRequestSettings
from musify.libraries.remote.spotify.api.item import SpotifyAPIItems
from musify.libraries.remote.spotify.api.misc import SpotifyAPIMisc
from musify.libraries.remote.spotify.api.playlist import SpotifyAPIPlaylists
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler
from musify.utils import safe_format_map, merge_maps

URL_AUTH = "https://accounts.spotify.com"

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
    "test_args": {"url": "{url}/me"},
    "test_condition": lambda r: "href" in r and "display_name" in r,
    "test_expiry": 600,
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}


class SpotifyAPI(SpotifyAPIMisc, SpotifyAPIItems, SpotifyAPIPlaylists):
    """
    Collection of endpoints for the Spotify API.

    :param client_id: The client ID to use when authorising requests.
    :param client_secret: The client secret to use when authorising requests.
    :param scopes: The scopes to request access to.
    :param cache: When given, attempt to use this cache for certain request types before calling the API.
    :param auth_kwargs: Optionally, provide kwargs to use when instantiating the :py:class:`APIAuthoriser`.
    """

    __slots__ = ()

    @property
    def user_id(self) -> str | None:
        """ID of the currently authenticated user"""
        if not self.user_data:
            try:
                self.user_data = self.get_self()
            except APIError:
                return None
        return self.user_data["id"]

    @property
    def user_name(self) -> str | None:
        """Name of the currently authenticated user"""
        if not self.user_data:
            try:
                self.user_data = self.get_self()
            except APIError:
                return None
        return self.user_data["display_name"]

    def __init__(
            self,
            client_id: str | None = None,
            client_secret: str | None = None,
            scopes: Iterable[str] = (),
            cache: ResponseCache | None = None,
            **auth_kwargs
    ):
        wrangler = SpotifyDataWrangler()

        format_map = {
            "client_id": client_id,
            "client_base64": base64.b64encode(f"{client_id}:{client_secret}".encode()).decode(),
            "scopes": " ".join(scopes),
            "url": wrangler.url_api
        }
        auth_kwargs = merge_maps(deepcopy(SPOTIFY_API_AUTH_ARGS), auth_kwargs)
        safe_format_map(auth_kwargs, format_map=format_map)

        auth_kwargs.pop("name", None)
        authoriser = APIAuthoriser(name=wrangler.source, **auth_kwargs)

        if cache is not None:  # TODO: implement and set storage getter function on cache
            cache.create_storage(SpotifyRequestSettings(name="tracks"))
            cache.create_storage(SpotifyRequestSettings(name="artists"))
            cache.create_storage(SpotifyRequestSettings(name="albums"))
            cache.create_storage(SpotifyRequestSettings(name="playlists"))
            cache.create_storage(SpotifyPaginatedRequestSettings(name="artist_albums"))
            cache.create_storage(SpotifyPaginatedRequestSettings(name="album_tracks"))
            cache.create_storage(SpotifyPaginatedRequestSettings(name="playlist_tracks"))

        super().__init__(authoriser=authoriser, wrangler=wrangler, cache=cache)
