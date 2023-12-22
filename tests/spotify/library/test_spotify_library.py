from copy import deepcopy
from random import randrange, sample
from typing import Any
from collections.abc import Iterable

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

    def test_load_playlists_responses(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        # load all when no include or exclude settings defined
        library = SpotifyLibrary(api=api, use_cache=False)

        pl_responses = library._get_playlists_data()
        assert len(pl_responses) == len(spotify_mock.user_playlists)
        for pl_response in pl_responses:
            assert len(pl_response["tracks"]["items"]) == pl_response["tracks"]["total"]

        # filter on include and exclude
        include = [pl["name"] for pl in spotify_mock.user_playlists[:20]]
        exclude = [pl["name"] for pl in spotify_mock.user_playlists[:10]]
        library = SpotifyLibrary(api=api, include=include, exclude=exclude, use_cache=False)

        pl_responses = library._get_playlists_data()
        assert len(pl_responses) == 10
        for pl_response in pl_responses:
            assert len(pl_response["tracks"]["items"]) == pl_response["tracks"]["total"]

    def test_load_track_responses(self, api: SpotifyAPI, spotify_mock: SpotifyMock):
        # only load tracks in playlists
        # make sure only to include playlists that do not include all available tracks
        include = [
            pl["name"] for pl in spotify_mock.user_playlists if pl["tracks"]["total"] < len(spotify_mock.user_playlists)
        ][:20]
        library = SpotifyLibrary(api=api, include=include, use_cache=False)
        pl_responses = library._get_playlists_data()
        for pl_response in pl_responses:
            assert len(pl_response["tracks"]["items"]) < len(spotify_mock.user_tracks)

        track_uris_in_playlists = [track["track"]["uri"] for pl in pl_responses for track in pl["tracks"]["items"]]
        expected = len([t for t in spotify_mock.user_tracks if t["track"]["uri"] in track_uris_in_playlists])
        assert expected > 0  # for the test to be valid

        assert len(library._get_tracks_data(pl_responses)) == expected

    def test_load(self):
        pass

    def test_enrich(self):
        pass

    def test_sync(self):
        pass

    def test_extend(self):
        pass

    def test_restore(self):
        pass

    def test_merge_playlists(self, library: SpotifyLibrary):
        pass
