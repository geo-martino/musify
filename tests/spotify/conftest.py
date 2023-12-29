import pytest

from syncify.spotify.api import SpotifyAPI
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
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
    """Yield an authorised :py:class:`SpotifyMock` object"""
    return spotify_mock
