from copy import deepcopy
from random import randrange, sample
from typing import Iterable

import pytest

from syncify.spotify.api import SpotifyAPI
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.library.library import SpotifyLibrary
from tests.remote.library.test_remote_collection import RemoteLibraryTester
from tests.spotify.api.mock import SpotifyMock


class TestSpotifyLibrary(RemoteLibraryTester):

    dict_json_equal = False

    @pytest.fixture
    def collection_merge_items(self, spotify_mock: SpotifyMock) -> Iterable[SpotifyTrack]:
        return [SpotifyTrack(spotify_mock.generate_track()) for _ in range(randrange(5, 10))]

    @pytest.fixture(scope="class")
    def _library(self, api: SpotifyAPI, spotify_mock: SpotifyMock) -> SpotifyLibrary:
        include = [pl["name"] for pl in sample(spotify_mock.user_playlists, k=10)]
        library = SpotifyLibrary(api=api, include=include, use_cache=False)
        library.load()
        return library

    @pytest.fixture
    def library(self, _library: SpotifyLibrary) -> SpotifyLibrary:
        return deepcopy(_library)

    def test_load(self, api: SpotifyAPI):
        library = SpotifyLibrary(api=api, use_cache=False)

        library.load()

    def test_extend(self):
        pass

    def test_merge_playlists(self, library: SpotifyLibrary):
        pass
