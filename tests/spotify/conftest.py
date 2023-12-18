import pytest

from syncify.spotify.api import SpotifyAPI
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.spotify.api.mock import SpotifyMock


@pytest.fixture(scope="session")
def spotify_wrangler():
    """Yields a :py:class:`SpotifyDataWrangler` for testing Spotify data wrangling"""
    return SpotifyDataWrangler()


@pytest.fixture(scope="module")
def api() -> SpotifyAPI:
    """Yield an authorised :py:class:`SpotifyAPI` object"""
    token = {"access_token": "fake access token", "token_type": "Bearer", "scope": "test-read"}
    return SpotifyAPI(name="test", token=token, cache_path=None)


@pytest.fixture(scope="session")
def spotify_mock(request) -> SpotifyMock:
    """Yield an authorised :py:class:`SpotifyMock` object"""
    with SpotifyMock() as m:
        yield m
