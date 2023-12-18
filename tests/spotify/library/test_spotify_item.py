from collections.abc import MutableMapping
from typing import Any

import pytest

from syncify.spotify.library.item import SpotifyTrack
from tests.spotify.api.mock import SpotifyMock


class TestSpotifyTrack:

    @pytest.fixture
    def response(self) -> dict[str, Any]:
        """Yield a valid response from the Spotify API for a track item type"""
        return SpotifyMock.generate_track(album=True, artists=True)

    @pytest.fixture
    def track(self, response: MutableMapping[str, Any]) -> SpotifyTrack:
        """Yield an initialised :py:class:`SpotifyTrack` from a given Spotify API response"""
        return SpotifyTrack(response)

    def test_attributes(self, track: SpotifyTrack):
        assert track.name
