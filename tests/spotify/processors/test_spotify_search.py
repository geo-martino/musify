import pytest

from syncify.local.collection import LocalAlbum
from syncify.local.track import LocalTrack
from syncify.remote.processors.search import ITEMS_SETTINGS, ALBUM_SETTINGS
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.library.collection import SpotifyAlbum
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.processors.processors import SpotifyItemSearcher
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.local.utils import random_track
from tests.remote.processors.test_remote_search import RemoteItemSearcherTester
from tests.spotify.api.mock import SpotifyMock


class TestSpotifyItemSearcher(RemoteItemSearcherTester):

    @pytest.fixture(scope="class")
    def remote_api(self, api: SpotifyAPI) -> SpotifyAPI:
        return api

    @pytest.fixture(scope="class")
    def remote_mock(self, spotify_mock: SpotifyMock) -> SpotifyMock:
        return spotify_mock

    @pytest.fixture(scope="class")
    def searcher(self, remote_api: SpotifyAPI, remote_mock: SpotifyMock) -> SpotifyItemSearcher:
        return SpotifyItemSearcher(api=remote_api)

    @pytest.fixture
    def search_items(self, spotify_mock: SpotifyMock, spotify_wrangler: SpotifyDataWrangler) -> list[LocalTrack]:
        items = []
        for remote_track in map(SpotifyTrack, spotify_mock.tracks[:ITEMS_SETTINGS.result_count]):
            local_track = random_track()
            local_track.uri = None
            local_track.remote_wrangler = spotify_wrangler

            local_track.title = remote_track.title
            local_track.album = remote_track.album
            local_track.artist = remote_track.artist
            local_track.file.info.length = remote_track.length
            local_track.year = remote_track.year

            items.append(local_track)

        return items

    @pytest.fixture
    def search_albums(
            self, api: SpotifyAPI, spotify_mock: SpotifyMock, spotify_wrangler: SpotifyDataWrangler
    ) -> list[LocalAlbum]:
        SpotifyAlbum.api = api
        SpotifyAlbum.check_total = False

        albums = []
        for album in map(SpotifyAlbum, spotify_mock.albums[:ALBUM_SETTINGS.result_count]):
            tracks = []
            for remote_track in album:
                local_track = random_track()
                local_track.uri = None
                local_track.remote_wrangler = spotify_wrangler
                local_track.compilation = True

                local_track.title = remote_track.title
                local_track.album = album.name
                local_track.artist = remote_track.artist
                local_track.year = remote_track.year
                local_track.file.info.length = remote_track.length

                tracks.append(local_track)

            albums.append(LocalAlbum(tracks=tracks, name=album.name))

        return albums
