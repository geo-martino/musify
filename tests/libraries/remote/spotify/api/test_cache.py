from random import choice

import pytest

from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.api.cache import SpotifyRequestSettings, SpotifyPaginatedRequestSettings
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler
from tests.libraries.remote.spotify.api.mock import SpotifyMock


class TestSpotifyRequestSettings:

    @pytest.fixture(scope="class")
    def settings(self) -> SpotifyRequestSettings:
        """Yields a :py:class:`SpotifyRequestSettings` object as a pytest.fixture."""
        return SpotifyRequestSettings(name="test")

    def test_core_getters(self, settings: SpotifyRequestSettings, api_mock: SpotifyMock):
        for responses in api_mock.item_type_map.values():
            response = choice(responses)
            name = response["display_name"] if response["type"] == "user" else response["name"]
            assert settings.get_name(response) == name
            assert settings.get_id(response["href"]) == response["id"]

        response = choice(api_mock.user_tracks)
        assert settings.get_name(response) is None

        url = f"{SpotifyDataWrangler.url_api}/me/tracks"
        assert settings.get_id(url) is None

    @pytest.fixture(scope="class")
    def settings_paginated(self) -> SpotifyPaginatedRequestSettings:
        """Yields a :py:class:`SpotifyPaginatedRequestSettings` object as a pytest.fixture."""
        return SpotifyPaginatedRequestSettings(name="test")

    def test_paginated_getters(
            self,
            settings_paginated: SpotifyPaginatedRequestSettings,
            api: SpotifyAPI,
            api_mock: SpotifyMock
    ):
        for parent, child in api.collection_item_map.items():
            response = choice(api_mock.item_type_map[parent])[child.name.lower() + "s"]
            url = response["href"]
            assert settings_paginated.get_offset(url) == response["offset"]
            assert settings_paginated.get_limit(url) == response["limit"]

        url = f"{SpotifyDataWrangler.url_api}/me/tracks"
        assert settings_paginated.get_offset(url) == 0
        assert settings_paginated.get_limit(url) == 50
