"""
Mixin for all implementations of :py:class:`RemoteAPI` for the Spotify API.

Also includes the default arguments to be used when requesting authorisation from the Spotify API.
"""
import base64
from collections.abc import Iterable
from copy import deepcopy

from yarl import URL

from musify import PROGRAM_NAME
from musify.api.authorise import APIAuthoriser
from musify.api.cache.backend.base import ResponseCache, ResponseRepository
from musify.api.cache.session import CachedSession
from musify.api.exception import APIError
from musify.libraries.remote.spotify.api.cache import SpotifyRequestSettings, SpotifyPaginatedRequestSettings
from musify.libraries.remote.spotify.api.item import SpotifyAPIItems
from musify.libraries.remote.spotify.api.misc import SpotifyAPIMisc
from musify.libraries.remote.spotify.api.playlist import SpotifyAPIPlaylists
from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler
from musify.utils import safe_format_map, merge_maps

URL_AUTH = "https://accounts.spotify.com"

# user authenticated access with scopes
SPOTIFY_API_AUTH_ARGS = {
    "auth_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "authorization_code",
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
            "state": PROGRAM_NAME,
            "scope": "{scopes}",
            "show_dialog": False,
        },
    },
    "refresh_args": {
        "url": f"{URL_AUTH}/api/token",
        "data": {
            "grant_type": "refresh_token",
        },
        "headers": {
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {client_base64}"
        },
    },
    "test_args": {"url": "{url}/me"},
    "test_condition": lambda r: SpotifyAPI.url_key in r and "display_name" in r,
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
            raise APIError(
                "User data not set. Either set explicitly or enter the "
                f"{self.__class__.__name__} context to set automatically."
            )
        return self.user_data["id"]

    @property
    def user_name(self) -> str | None:
        """Name of the currently authenticated user"""
        if not self.user_data:
            raise APIError(
                "User data not set. Either set explicitly or enter the "
                f"{self.__class__.__name__} context to set automatically."
            )
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
            "url": str(wrangler.url_api)
        }
        auth_kwargs = merge_maps(deepcopy(SPOTIFY_API_AUTH_ARGS), auth_kwargs, extend=False, overwrite=True)
        safe_format_map(auth_kwargs, format_map=format_map)

        auth_kwargs.pop("name", None)
        authoriser = APIAuthoriser(name=wrangler.source, **auth_kwargs)

        super().__init__(authoriser=authoriser, wrangler=wrangler, cache=cache)

    # noinspection PyAsyncCall
    async def _setup_cache(self) -> None:
        if not isinstance(self.handler.session, CachedSession):
            return

        cache = self.handler.session.cache
        cache.repository_getter = self._get_cache_repository

        cache.create_repository(SpotifyRequestSettings(name="tracks"))
        cache.create_repository(SpotifyRequestSettings(name="audio_features"))
        cache.create_repository(SpotifyRequestSettings(name="audio_analysis"))

        cache.create_repository(SpotifyRequestSettings(name="albums"))
        cache.create_repository(SpotifyPaginatedRequestSettings(name="album_tracks"))

        cache.create_repository(SpotifyRequestSettings(name="artists"))
        cache.create_repository(SpotifyPaginatedRequestSettings(name="artist_albums"))

        cache.create_repository(SpotifyRequestSettings(name="shows"))
        cache.create_repository(SpotifyRequestSettings(name="episodes"))
        cache.create_repository(SpotifyPaginatedRequestSettings(name="show_episodes"))

        cache.create_repository(SpotifyRequestSettings(name="audiobooks"))
        cache.create_repository(SpotifyRequestSettings(name="chapters"))
        cache.create_repository(SpotifyPaginatedRequestSettings(name="audiobook_chapters"))

        await cache

    @staticmethod
    def _get_cache_repository(cache: ResponseCache, url: str | URL) -> ResponseRepository | None:
        path = URL(url).path
        path_split = [part.replace("-", "_") for part in path.split("/")[2:]]

        if len(path_split) < 3:
            name = path_split[0]
        else:
            name = "_".join([path_split[0].rstrip("s"), path_split[2].rstrip("s") + "s"])

        return cache.get(name)
