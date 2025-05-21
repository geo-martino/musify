import pytest
from faker import Faker

from musify.model import MusifyModel
# noinspection PyProtectedMember
from musify.model.collection.library import _HasTracksAndPlaylistsMixin
from musify.model.collection.playlist import Playlist
from musify.model.item.track import Track
from tests.model.testers import MusifyResourceTester


class TestLibrary(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return _HasTracksAndPlaylistsMixin()

    def test_tracks_in_playlists(self, tracks: list[Track], playlists: list[Playlist]) -> None:
        for pl in playlists:
            tracks += pl.tracks[:len(pl.tracks) // 2]

        library = _HasTracksAndPlaylistsMixin(tracks=tracks, playlists=playlists)
        assert all(track not in library.tracks for track in library.tracks_in_playlists)
        assert library.tracks_in_playlists == [track for pl in playlists for track in pl.tracks]
