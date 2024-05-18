import pytest

from musify.api.cache.backend.base import ResponseCache, PaginatedRequestSettings
from musify.api.cache.backend.sqlite import SQLiteCache
from musify.libraries.remote.spotify.api import SpotifyAPI
from tests.libraries.remote.spotify.utils import random_id
from tests.utils import random_str


class TestSpotifyAPI:

    @pytest.fixture
    def cache(self) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        return SQLiteCache.connect_with_in_memory_db()

    def test_init_authoriser(self, cache: ResponseCache):
        client_id = "CLIENT_ID"
        client_secret = "CLIENT_SECRET"
        scopes = ["scope 1", "scope 2"]
        token_file_path = "i am a path to a file.json"

        api = SpotifyAPI(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            cache=cache,
            token_file_path=token_file_path,
            name="this name won't be used",
        )

        assert api.handler.authoriser.name == api.wrangler.source
        assert api.handler.authoriser.user_args["params"]["client_id"] == client_id
        assert api.handler.authoriser.user_args["params"]["scope"] == " ".join(scopes)
        assert api.handler.authoriser.token_file_path == token_file_path

        assert api.handler.cache.cache_name == cache.cache_name

    def test_init_cache(self, cache: ResponseCache):
        SpotifyAPI(cache=cache)

        expected_names_normal = [
            "tracks",
            "audio_features",
            "audio_analysis",
            "albums",
            "artists",
            "episodes",
            "chapters",
        ]
        expected_names_paginated = ["album_tracks", "artist_albums", "show_episodes", "audiobook_chapters"]

        assert all(name in cache for name in expected_names_normal)
        assert all(name in cache for name in expected_names_paginated)

        assert all(not isinstance(cache[name].settings, PaginatedRequestSettings) for name in expected_names_normal)
        assert all(isinstance(cache[name].settings, PaginatedRequestSettings) for name in expected_names_paginated)

    def test_init_cache_repository_getter(self, cache: ResponseCache):
        api = SpotifyAPI(cache=cache)

        name_url_map = {
            "tracks": f"{api.wrangler.url_api}/tracks/{random_id()}",
            "artists": f"{api.wrangler.url_api}/artists?ids={",".join(random_id() for _ in range(10))}",
            "albums": f"{api.wrangler.url_api}/albums?ids={",".join(random_id() for _ in range(50))}",
        }
        names_paginated = ["artist_albums", "album_tracks"]
        for name in names_paginated:
            parent, child = name.split("_")
            parent = parent.rstrip("s") + "s"
            child = child.rstrip("s") + "s"

            url = f"{api.wrangler.url_api}/{parent}/{random_id()}/{child}"
            name_url_map[name] = url

        for name, url in name_url_map.items():
            repository = cache.get_repository_from_url(url)
            assert repository.settings.name == name

        # un-cached URLs
        assert cache.get_repository_from_url(f"{api.wrangler.url_api}/me/albums") is None
        assert cache.get_repository_from_url(f"{api.wrangler.url_api}/search") is None
        assert cache.get_repository_from_url(f"{api.wrangler.url_api}/playlists/{random_id()}/followers") is None
        assert cache.get_repository_from_url(f"{api.wrangler.url_api}/users/{random_str(10, 30)}/playlists") is None
