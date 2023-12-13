from datetime import datetime

import pytest

from syncify.local.track import LocalTrack
from syncify.processors.limit import ItemLimiter, LimitType
from tests.abstract.misc import PrettyPrinterTester
from tests.local.track.utils import random_tracks
from tests.utils import random_file


# TODO: add test for to_xml

class TestItemComparer(PrettyPrinterTester):

    @staticmethod
    @pytest.fixture
    def obj() -> ItemLimiter:
        return ItemLimiter(limit=30, on=LimitType.MINUTES, sorted_by="HighestRating", allowance=2)

    @staticmethod
    @pytest.fixture
    def tracks(tmp_path: str) -> list[LocalTrack]:
        """Yields a list of random tracks with dynamically configured properties for limit tests"""
        tracks = random_tracks(50)
        for i in range(1, 6):
            random_file_path = random_file(tmp_path=tmp_path, size=i * 1000)
            for track in tracks[(i-1)*10:i*10]:

                track.album = f"album {i}"
                track.file.info.length = i * 60
                track._path = random_file_path
                track.rating = i

                if i != 1 and i != 5:
                    track.last_played = datetime.now()

                if i == 1 or i == 3:
                    track.play_count = 1000000

        return tracks

    @staticmethod
    def test_init():
        limiter = ItemLimiter(sorted_by="HighestRating")
        assert limiter._processor == limiter._highest_rating

        limiter = ItemLimiter(sorted_by="__ least_ recently_  added __ ")
        assert limiter._processor == limiter._least_recently_added

        limiter = ItemLimiter(sorted_by="__most recently played__")
        assert limiter._processor == limiter._most_recently_played

    @staticmethod
    def test_limit_below_threshold(tracks: list[LocalTrack]):
        assert len(tracks) == 50

        limiter = ItemLimiter()
        limiter.limit(tracks)
        assert len(tracks) == 50

        limiter = ItemLimiter(on=LimitType.ITEMS)
        limiter.limit(tracks)
        assert len(tracks) == 50

    @staticmethod
    def test_limit_on_items_1(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=25)
        limiter.limit(tracks)
        assert len(tracks) == 25

    @staticmethod
    def test_limit_on_items_2(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=10, sorted_by="HighestRating")
        limiter.limit(tracks)
        assert len(tracks) == 10
        assert set(track.album for track in tracks) == {"album 5"}

    @staticmethod
    def test_limit_on_items_3(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=20, sorted_by="most often played")
        limiter.limit(tracks)
        assert len(tracks) == 20
        assert set(track.album for track in tracks) == {"album 1", "album 3"}

    @staticmethod
    def test_limit_on_items_4(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=20, sorted_by="most often played")
        limiter.limit(tracks, ignore=[track for track in tracks if track.album == "album 5"])
        assert len(tracks) == 30
        assert set(track.album for track in tracks) == {"album 1", "album 3", "album 5"}

    @staticmethod
    def test_limit_on_albums_1(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=3, on=LimitType.ALBUMS)
        limiter.limit(tracks)
        assert len(tracks) == 30

    @staticmethod
    def test_limit_on_albums_2(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
        limiter.limit(tracks)
        assert len(tracks) == 20
        assert set(track.album for track in tracks) == {"album 1", "album 5"}

    @staticmethod
    def test_limit_on_albums_3(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
        limiter.limit(tracks, ignore={track for track in tracks if track.album == "album 3"})
        assert len(tracks) == 30
        assert set(track.album for track in tracks) == {"album 1", "album 3", "album 5"}

    @staticmethod
    def test_limit_on_seconds_1(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=30, on=LimitType.MINUTES)
        limiter.limit(tracks)
        assert len(tracks) == 20

    @staticmethod
    def test_limit_on_seconds_2(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=30, on=LimitType.MINUTES, allowance=2)
        limiter.limit(tracks)
        assert len(tracks) == 21

    @staticmethod
    def test_limit_on_bytes_1(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=30, on=LimitType.KILOBYTES)
        limiter.limit(tracks)
        assert len(tracks) == 20

    @staticmethod
    def test_limit_on_bytes_2(tracks: list[LocalTrack]):
        limiter = ItemLimiter(limit=30, on=LimitType.KILOBYTES, allowance=2)
        limiter.limit(tracks)
        assert len(tracks) == 21
