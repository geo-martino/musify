"""
Mixin for all implementations of :py:class:`RemoteAPI` for the Spotify API.

Also includes the default arguments to be used when requesting authorisation from the Spotify API.
"""
from http import HTTPMethod
from pathlib import Path

from aiohttp import ClientResponse
from aiorequestful.auth.oauth2 import AuthorisationCodeFlow
from aiorequestful.auth.utils import AuthRequest
from aiorequestful.cache.backend.base import ResponseCache, ResponseRepository
from aiorequestful.cache.session import CachedSession
from aiorequestful.types import URLInput
from yarl import URL

from musify.libraries.remote.core.exception import APIError
from musify.libraries.remote.spotify.api.cache import SpotifyRepositorySettings, SpotifyPaginatedRepositorySettings
from musify.libraries.remote.spotify.api.item import SpotifyAPIItems
from musify.libraries.remote.spotify.api.misc import SpotifyAPIMisc
from musify.libraries.remote.spotify.api.playlist import SpotifyAPIPlaylists
from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler
from musify.types import UnitIterable


class SpotifyAPI(SpotifyAPIMisc, SpotifyAPIItems, SpotifyAPIPlaylists):
    """
    Collection of endpoints for the Spotify API.

    :param client_id: The client ID to use when authorising requests.
    :param client_secret: The client secret to use when authorising requests.
    :param scope: The scopes to request access to.
    :param cache: When given, attempt to use this cache for certain request types before calling the API.
    :param token_file_path: Optionally, provide a path to save/load a response token.
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

    _url_auth = URL.build(scheme="https", host="accounts.spotify.com")

    def __init__(
            self,
            client_id: str | None = None,
            client_secret: str | None = None,
            scope: UnitIterable[str] = (),
            cache: ResponseCache | None = None,
            token_file_path: str | Path = None,
    ):
        wrangler = SpotifyDataWrangler()
        authoriser = AuthorisationCodeFlow.create_with_encoded_credentials(
            service_name=wrangler.source,
            user_request_url=self._url_auth.with_path("authorize"),
            token_request_url=self._url_auth.with_path("api/token"),
            refresh_request_url=self._url_auth.with_path("api/token"),
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
        )

        if not hasattr(authoriser.token_request, "headers"):
            authoriser.token_request.headers = {}
        authoriser.token_request.headers["content-type"] = "application/x-www-form-urlencoded"

        if not hasattr(authoriser.refresh_request, "headers"):
            authoriser.refresh_request.headers = {}
        authoriser.refresh_request.headers["content-type"] = "application/x-www-form-urlencoded"

        if token_file_path:
            authoriser.response.file_path = Path(token_file_path)
        authoriser.response.additional_headers = {
            "Accept": "application/json", "Content-Type": "application/json"
        }

        authoriser.tester.request = AuthRequest(
            method=HTTPMethod.GET, url=wrangler.url_api.joinpath("me")
        )
        authoriser.tester.response_test = self._response_test
        authoriser.tester.max_expiry = 600

        super().__init__(authoriser=authoriser, wrangler=wrangler, cache=cache)

    async def _response_test(self, response: ClientResponse) -> bool:
        r = await response.json()
        return self.url_key in r and "display_name" in r

    # noinspection PyAsyncCall
    async def _setup_cache(self) -> None:
        session = self.handler.session
        if not isinstance(session, CachedSession):
            return

        cache = session.cache
        cache.repository_getter = self._get_cache_repository

        cache.create_repository(SpotifyRepositorySettings(name="tracks"))
        cache.create_repository(SpotifyRepositorySettings(name="audio_features"))
        cache.create_repository(SpotifyRepositorySettings(name="audio_analysis"))

        cache.create_repository(SpotifyRepositorySettings(name="albums"))
        cache.create_repository(SpotifyPaginatedRepositorySettings(name="album_tracks"))

        cache.create_repository(SpotifyRepositorySettings(name="artists"))
        cache.create_repository(SpotifyPaginatedRepositorySettings(name="artist_albums"))

        cache.create_repository(SpotifyRepositorySettings(name="shows"))
        cache.create_repository(SpotifyRepositorySettings(name="episodes"))
        cache.create_repository(SpotifyPaginatedRepositorySettings(name="show_episodes"))

        cache.create_repository(SpotifyRepositorySettings(name="audiobooks"))
        cache.create_repository(SpotifyRepositorySettings(name="chapters"))
        cache.create_repository(SpotifyPaginatedRepositorySettings(name="audiobook_chapters"))

        await cache

    @staticmethod
    def _get_cache_repository(cache: ResponseCache, url: URLInput) -> ResponseRepository | None:
        path = URL(url).path
        path_split = [part.replace("-", "_") for part in path.split("/")[2:]]

        if len(path_split) < 3:
            name = path_split[0]
        else:
            name = "_".join([path_split[0].rstrip("s"), path_split[2].rstrip("s") + "s"])

        return cache.get(name)
