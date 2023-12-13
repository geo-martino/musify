import pytest

from syncify.local.track import LocalTrack, FLAC, M4A, MP3, WMA
from tests.local.track.track_tester import LocalTrackTester
from tests.local.track.utils import path_track_flac, path_track_mp3, path_track_m4a, path_track_wma
from tests.local.utils import remote_wrangler


class TestFLAC(LocalTrackTester):

    @property
    def track_class(self):
        return FLAC

    @property
    def track_count(self):
        return 2

    @pytest.fixture(params=[path_track_flac])
    def track(self, path: str) -> LocalTrack:
        return self.load_track(path)

    def test_loaded_attributes(self, track: LocalTrack):
        assert track.tag_sep == "; "

        # metadata
        assert track.title == "title 1"
        assert track.artist == "artist 1"
        assert track.artists == ["artist 1"]
        assert track.album == "album artist 1"
        assert track.album_artist == "various"
        assert track.track_number == 1
        assert track.track_total == 4
        assert track.genres == ["Pop", "Rock", "Jazz"]
        assert track.year == 2020
        assert track.bpm == 120.12
        assert track.key == 'A'
        assert track.disc_number == 1
        assert track.disc_total == 3
        assert track.compilation
        # noinspection SpellCheckingInspection
        assert track.comments == ["spotify:track:6fWoFduMpBem73DMLCOh1Z"]

        assert track.uri == track.comments[0]
        assert track.has_uri

        # file properties
        assert int(track.length) == 20
        # assert track.path == path_track_flac  # uses tmp_path instead
        assert track.ext == ".flac"
        assert track.size == 1818191
        assert track.channels == 1
        assert track.bit_rate == 706.413
        assert track.bit_depth == 0.016
        assert track.sample_rate == 44.1


class TestMP3(LocalTrackTester):

    @property
    def track_class(self):
        return MP3

    @property
    def track_count(self):
        return 2

    @pytest.fixture(params=[path_track_mp3])
    def track(self, path: str) -> LocalTrack:
        return self.load_track(path)

    def test_loaded_attributes(self, track: LocalTrack):
        assert track.tag_sep == "; "

        # metadata
        assert track.title == "title 2"
        assert track.artist == "artist 2; another artist"
        assert track.artists == ["artist 2", "another artist"]
        assert track.album == "album artist 2"
        assert track.album_artist == "various"
        assert track.track_number == 3
        assert track.track_total == 4
        assert track.genres == ["Pop Rock", "Musical"]
        assert track.year == 2024
        assert track.bpm == 200.56
        assert track.key == 'C'
        assert track.disc_number == 2
        assert track.disc_total == 3
        assert not track.compilation
        # noinspection SpellCheckingInspection
        assert track.comments == ["spotify:track:1TjVbzJUAuOvas1bL00TiH"]

        assert track.uri == track.comments[0]
        assert track.has_uri

        # file properties
        assert int(track.length) == 30
        # assert track.path == path_track_mp3  # uses tmp_path instead
        assert track.ext == ".mp3"
        assert track.size == 411038
        assert track.channels == 1
        assert track.bit_rate == 96.0
        assert track.bit_depth is None
        assert track.sample_rate == 44.1


class TestM4A(LocalTrackTester):

    @property
    def track_class(self):
        return M4A

    @property
    def track_count(self):
        return 1

    @pytest.fixture(params=[path_track_m4a])
    def track(self, path: str) -> LocalTrack:
        return self.load_track(path)

    def test_loaded_attributes(self, track: LocalTrack):
        assert track.tag_sep == "; "

        # metadata
        assert track.title == "title 3"
        assert track.artist == "artist 3"
        assert track.artists == ["artist 3"]
        assert track.album == "album artist 3"
        assert track.album_artist == "various"
        assert track.track_number == 2
        assert track.track_total == 4
        assert track.genres == ["Dance", "Techno"]
        assert track.year == 2021
        assert track.bpm == 120.0
        assert track.key == 'B'
        assert track.disc_number == 1
        assert track.disc_total == 2
        assert track.compilation
        assert track.comments == ["spotify:track:4npv0xZO9fVLBmDS2XP9Bw"]

        assert track.uri == track.comments[0]
        assert track.has_uri

        # file properties
        assert int(track.length) == 20
        # assert track.path == path_track_m4a  # uses tmp_path instead
        assert track.ext == ".m4a"
        assert track.size == 302199
        assert track.channels == 2
        assert track.bit_rate == 98.17
        assert track.bit_depth == 0.016
        assert track.sample_rate == 44.1


class TestWMA(LocalTrackTester):

    @property
    def track_class(self):
        return WMA

    @property
    def track_count(self):
        return 1

    @pytest.fixture(params=[path_track_wma])
    def track(self, path: str) -> LocalTrack:
        return self.load_track(path)

    def test_loaded_attributes(self, track: LocalTrack):
        assert track.tag_sep == "; "

        # metadata
        assert track.title == "title 4"
        assert track.artist == "artist 4"
        assert track.artists == ["artist 4"]
        assert track.album == "album artist 4"
        assert track.album_artist == "various"
        assert track.track_number == 4
        assert track.track_total == 4
        assert track.genres == ["Metal", "Rock"]
        assert track.year == 2023
        assert track.bpm == 200.56
        assert track.key == 'D'
        assert track.disc_number == 3
        assert track.disc_total == 4
        assert not track.compilation
        assert track.comments == [remote_wrangler.unavailable_uri_dummy]

        assert track.uri is None
        assert not track.has_uri

        # file properties
        assert int(track.length) == 32
        # assert track.path == path_track_wma  # uses tmp_path instead
        assert track.ext == ".wma"
        assert track.size == 1193637
        assert track.channels == 1
        assert track.bit_rate == 96.0
        assert track.bit_depth is None
        assert track.sample_rate == 44.1
