from copy import deepcopy
from random import sample
from urllib.parse import parse_qs

import pytest

from syncify.spotify.api import SpotifyAPI
from syncify.spotify.library.library import SpotifyLibrary
from syncify.spotify.library.object import SpotifyTrack
from tests.remote.library.library import RemoteLibraryTester
from tests.spotify.api.mock import SpotifyMock


class TestSpotifyLibrary(RemoteLibraryTester):

    dict_json_equal = False

    @pytest.fixture
    def collection_merge_items(self, api_mock: SpotifyMock) -> list[SpotifyTrack]:
        tracks = [SpotifyTrack(track) for track in api_mock.tracks[api_mock.range_max: api_mock.range_max + 10]]
        assert len(tracks) > 4
        return tracks

    @pytest.fixture(scope="class")
    def _library(self, api: SpotifyAPI, api_mock: SpotifyMock) -> SpotifyLibrary:
        include = [pl["name"] for pl in sample(api_mock.user_playlists, k=10)]

        library = SpotifyLibrary(api=api, include=include, use_cache=False)
        library.load()

        return library

    @pytest.fixture
    def library(self, _library: SpotifyLibrary) -> SpotifyLibrary:
        return deepcopy(_library)

    def test_load_playlists_responses(self, api: SpotifyAPI, api_mock: SpotifyMock):
        # load all when no include or exclude settings defined
        library = SpotifyLibrary(api=api, use_cache=False)

        pl_responses = library._get_playlists_data()
        assert len(pl_responses) == len(api_mock.user_playlists)
        for pl_response in pl_responses:
            assert len(pl_response["tracks"]["items"]) == pl_response["tracks"]["total"]

        # filter on include and exclude
        include = [pl["name"] for pl in api_mock.user_playlists[:20]]
        exclude = [pl["name"] for pl in api_mock.user_playlists[:10]]
        library = SpotifyLibrary(api=api, include=include, exclude=exclude, use_cache=False)

        pl_responses = library._get_playlists_data()
        assert len(pl_responses) == 10
        for pl_response in pl_responses:
            assert len(pl_response["tracks"]["items"]) == pl_response["tracks"]["total"]

    def test_load_track_responses(self, api: SpotifyAPI, api_mock: SpotifyMock):
        # make sure only to include playlists that do not include all available tracks
        include = [pl["name"] for pl in api_mock.user_playlists[:20]]

        library = SpotifyLibrary(api=api, include=include, use_cache=False)
        pl_responses = library._get_playlists_data()
        for pl_response in pl_responses:
            assert len(pl_response["tracks"]["items"]) < len(api_mock.user_tracks)

        # only load tracks in playlists
        in_playlists = [track["track"]["uri"] for pl in pl_responses for track in pl["tracks"]["items"]]
        expected = len([t for t in api_mock.user_tracks if t["track"]["uri"] in in_playlists])
        assert expected > 0  # for the test to be valid

        assert len(library._get_tracks_data(pl_responses)) == expected

    def test_load(self, api: SpotifyAPI):
        library = SpotifyLibrary(api=api, use_cache=False)
        pl_data = library._get_playlists_data()
        track_data = library._get_tracks_data(pl_data)

        library.load()

        assert len(library.tracks) == len(track_data)
        assert len(library.playlists) == len(pl_data)
        for pl in library.playlists.values():
            assert len(pl.tracks) == pl.track_total

    # noinspection PyMethodOverriding
    def test_enrich_tracks(self, library, api_mock: SpotifyMock):
        def validate_album_not_enriched(t: SpotifyTrack) -> None:
            """Check album does not contain expected enriched fields"""
            assert "external_ids" not in t.response["album"]
            assert "genres" not in t.response["album"]
            assert "popularity" not in t.response["album"]

        def validate_artists_not_enriched(t: SpotifyTrack) -> None:
            """Check artists do not contain expected enriched fields"""
            for art in t.response["artists"]:
                assert "followers" not in art
                assert "images" not in art
                assert "popularity" not in art

        api_mock.reset_mock()  # test checks the number of requests made

        # ensure tracks are not enriched already
        artist_ids = {artist["id"] for track in library.tracks for artist in track.response["artists"]}
        album_ids = {track.response["album"]["id"] for track in library.tracks}
        track_album_map = {track.uri: track.album for track in library.tracks}
        track_artists_map = {track.uri: [a.name for a in track.artists] for track in library.tracks}
        for track in library.tracks:
            validate_album_not_enriched(track)
            validate_artists_not_enriched(track)

        # enriches only albums
        library.enrich_tracks(albums=True, artists=False)
        for track in library.tracks:
            assert track.album == track_album_map[track.uri]
            assert "external_ids" in track.response["album"]
            assert "genres" in track.response["album"]
            assert "popularity" in track.response["album"]
            assert "tracks" not in track.response["album"]

            validate_artists_not_enriched(track)

            assert len(api_mock.get_requests(url=track.response["album"]["href"] + "/tracks")) == 0

        # check requests
        assert len(api_mock.get_requests(url=library.api.api_url_base + "/artists")) == 0
        req_albums = api_mock.get_requests(url=library.api.api_url_base + "/albums")
        req_album_ids = {id_ for req in req_albums for id_ in parse_qs(req.query)["ids"][0].split(",")}
        assert req_album_ids == album_ids

        api_mock.reset_mock()

        # enriches artists without replacing previous enrichment
        library.enrich_tracks(albums=False, artists=True)
        for track in library.tracks:
            assert track.album == track_album_map[track.uri]
            assert "external_ids" in track.response["album"]
            assert "genres" in track.response["album"]
            assert "popularity" in track.response["album"]
            assert "tracks" not in track.response["album"]

            assert len(api_mock.get_requests(url=track.response["album"]["href"] + "/tracks")) == 0

            assert [a.name for a in track.artists] == track_artists_map[track.uri]
            for artist in track.response["artists"]:
                assert "followers" in artist
                assert "images" in artist
                assert "popularity" in artist

        # check requests
        assert len(api_mock.get_requests(url=library.api.api_url_base + "/albums")) == 0
        req_artists = api_mock.get_requests(url=library.api.api_url_base + "/artists")
        req_artist_ids = {id_ for req in req_artists for id_ in parse_qs(req.query)["ids"][0].split(",")}
        assert req_artist_ids == artist_ids

    def test_merge_playlists(self, library: SpotifyLibrary):
        pass
