import pytest

from syncify.spotify.api import SpotifyAPI
from tests.spotify.api.mock import SpotifyMock


@pytest.fixture(scope="module")
def api() -> SpotifyAPI:
    """Yield an authorised :py:class:`SpotifyAPI` object"""
    token = {
        "access_token": "fake access token",
        "token_type": "Bearer",
        "scope": "test-read"
    }
    return SpotifyAPI(name="test", token=token, cache_path=None)


@pytest.fixture(scope="module")
def spotify_mock(request) -> SpotifyMock:
    """Yield an authorised :py:class:`SpotifyMock` object"""
    with SpotifyMock() as m:
        yield m
