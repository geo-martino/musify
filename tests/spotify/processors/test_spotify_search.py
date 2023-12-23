import pytest

from syncify.abstract.enums import TagFieldCombined as Tag
from syncify.local.collection import LocalAlbum
from syncify.local.track import LocalTrack
from syncify.remote.processors.search import SearchSettings
from syncify.processors.match import CleanTagConfig
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
        SpotifyItemSearcher.karaoke_tags = {"karaoke", "backing", "instrumental"}
        SpotifyItemSearcher.year_range = 10

        SpotifyItemSearcher.clean_tags_remove_all = {"the", "a", "&", "and"}
        SpotifyItemSearcher.clean_tags_split_all = set()
        SpotifyItemSearcher.clean_tags_config = (
            CleanTagConfig(tag=Tag.TITLE, _remove={"part"}, _split={"featuring", "feat.", "ft.", "/"}),
            CleanTagConfig(tag=Tag.ARTIST, _split={"featuring", "feat.", "ft.", "vs"}),
            CleanTagConfig(tag=Tag.ALBUM, _remove={"ep"}, _preprocess=lambda x: x.split('-')[0])
        )

        SpotifyItemSearcher.reduce_name_score_on = {"live", "demo", "acoustic"}
        SpotifyItemSearcher.reduce_name_score_factor = 0.5

        SpotifyItemSearcher.settings_items = SearchSettings(
            search_fields_1=[Tag.TITLE],
            match_fields={Tag.TITLE},
            result_count=10,
            allow_karaoke=True,
            min_score=0.1,
            max_score=0.5
        )
        SpotifyItemSearcher.settings_albums = SearchSettings(
            search_fields_1=[Tag.ALBUM],
            match_fields={Tag.ALBUM},
            result_count=5,
            allow_karaoke=True,
            min_score=0.1,
            max_score=0.5
        )

        return SpotifyItemSearcher(api=remote_api)

    @pytest.fixture
    def search_items(
            self, searcher: SpotifyItemSearcher, spotify_mock: SpotifyMock, spotify_wrangler: SpotifyDataWrangler
    ) -> list[LocalTrack]:
        items = []
        for remote_track in map(SpotifyTrack, spotify_mock.tracks[:searcher.settings_items.result_count]):
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
            self,
            searcher: SpotifyItemSearcher,
            api: SpotifyAPI,
            spotify_mock: SpotifyMock,
            spotify_wrangler: SpotifyDataWrangler
    ) -> list[LocalAlbum]:
        SpotifyAlbum.api = api
        SpotifyAlbum.check_total = False

        albums = []
        for album in map(SpotifyAlbum, spotify_mock.albums[:searcher.settings_items.result_count]):
            tracks = []
            for remote_track in album:
                local_track = random_track()
                local_track.uri = None
                local_track.remote_wrangler = spotify_wrangler
                local_track.compilation = False

                local_track.title = remote_track.title
                local_track.album = album.name
                local_track.artist = remote_track.artist
                local_track.year = remote_track.year
                local_track.file.info.length = remote_track.length

                tracks.append(local_track)

            albums.append(LocalAlbum(tracks=tracks, name=album.name))

        return albums
