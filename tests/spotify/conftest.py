import pytest

from syncify.spotify.processors.wrangle import SpotifyDataWrangler


@pytest.fixture(scope="session")
def wrangler():
    """Yields a :py:class:`SpotifyDataWrangler` for testing Spotify data wrangling"""
    return SpotifyDataWrangler()
