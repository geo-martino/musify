from urllib.parse import urlparse, parse_qs

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings
from musify.api.exception import CacheError
from musify.libraries.remote.core.enum import RemoteIDType
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler


class SpotifyRequestSettings(RequestSettings):

    wrangler = SpotifyDataWrangler()

    def get_id(self, url: str) -> str:
        if "/me" in url.rstrip("/"):
            raise CacheError("Cannot get IDs for 'me' endpoints")
        return self.wrangler.convert(url, type_in=RemoteIDType.URL, type_out=RemoteIDType.ID)


class SpotifyPaginatedRequestSettings(PaginatedRequestSettings, SpotifyRequestSettings):

    def get_offset(self, url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("offset", [0])[0])

    def get_limit(self, url: str) -> int:
        params = parse_qs(urlparse(url).query)
        return int(params.get("limit", [50])[0])
