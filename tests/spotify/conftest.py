import pytest

from musify.spotify.api import SpotifyAPI
from musify.spotify.processors import SpotifyDataWrangler
from tests.spotify.api.mock import SpotifyMock


@pytest.fixture(scope="module")
def wrangler(spotify_wrangler: SpotifyDataWrangler):
    """Yields a :py:class:`SpotifyDataWrangler` for testing Spotify data wrangling"""
    return spotify_wrangler


@pytest.fixture(scope="module")
def api(spotify_api: SpotifyAPI, api_mock: SpotifyMock) -> SpotifyAPI:
    """Yield an authorised :py:class:`SpotifyAPI` object"""
    return spotify_api


@pytest.fixture(scope="module")
def api_mock(spotify_mock: SpotifyMock) -> SpotifyMock:
    """Yield a :py:class:`SpotifyMock` object with valid mock data ready to be called via HTTP requests"""
    return spotify_mock
