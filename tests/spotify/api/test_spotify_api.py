from typing import Any

import pytest

from syncify.spotify.api import SpotifyAPI
from tests.spotify.api.collection import SpotifyAPICollectionsTester
from tests.spotify.api.core import SpotifyAPICoreTester
from tests.spotify.api.item import SpotifyAPIItemsTester


class TestSpotifyAPI(SpotifyAPICoreTester, SpotifyAPIItemsTester, SpotifyAPICollectionsTester):

    @staticmethod
    @pytest.fixture(scope="class")
    def api(token: dict[str, Any]) -> SpotifyAPI:
        """Yield an authorised :py:class:`SpotifyAPI` object"""
        return SpotifyAPI(name="test", token=token, cache_path=None)

    @staticmethod
    @pytest.fixture(scope="class")
    def token() -> dict[str, Any]:
        """Yield a basic token example"""
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "scope": "test-read"
        }
