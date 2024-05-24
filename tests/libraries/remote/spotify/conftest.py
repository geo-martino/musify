from copy import copy

import pytest

from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler
from tests.libraries.remote.spotify.api.mock import SpotifyMock


@pytest.fixture(scope="module")
def wrangler(spotify_wrangler: SpotifyDataWrangler):
    """Yields a :py:class:`SpotifyDataWrangler` for testing Spotify data wrangling"""
    return spotify_wrangler


@pytest.fixture(scope="module")
def api(spotify_api: SpotifyAPI) -> SpotifyAPI:
    """Yield an authorised :py:class:`SpotifyAPI` object"""
    return spotify_api


@pytest.fixture(scope="module")
def _api_mock(spotify_mock: SpotifyMock) -> SpotifyMock:
    """
    Yield an authorised and configured :py:class:`SpotifyMock` object with
    valid mock data ready to be called via HTTP requests.
    """
    return spotify_mock


@pytest.fixture
def api_mock(_api_mock: SpotifyMock) -> SpotifyMock:
    """
    Yield an authorised and configured :py:class:`SpotifyMock` object with
    valid mock data ready to be called via HTTP requests.
    Creates a copy of ``_api_mock`` to allow for successful requests history assertions.
    """
    mock = copy(_api_mock)
    mock.reset()
    return mock
