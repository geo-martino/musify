import os
from copy import copy
from datetime import datetime

from syncify.processor.limit import ItemLimiter, LimitType
from syncify.local.track import LocalTrack
from tests.common import random_file
from tests.local.track.common import random_tracks

# TODO: add tests for new exception cases


def test_init():
    limiter = ItemLimiter(sorted_by="HighestRating")
    assert limiter._processor == limiter._highest_rating

    limiter = ItemLimiter(sorted_by="__ least_ recently_  added __ ")
    assert limiter._processor == limiter._least_recently_added

    limiter = ItemLimiter(sorted_by="__most recently played__")
    assert limiter._processor == limiter._most_recently_played


def get_tracks_for_limit_test() -> tuple[list[LocalTrack], list[str]]:
    """Generate a list of random tracks with dynamically configured properties for limit tests"""
    # prepare tracks for tests
    tracks = random_tracks(50)
    random_files = []
    for i in range(1, 6):
        random_file_path = random_file(i * 1000)
        random_files.append(random_file_path)
        for track in tracks[(i-1)*10:i*10]:

            track.album = f"album {i}"
            track.file.info.length = i * 60
            track._path = random_file_path
            track.rating = i

            if i != 1 and i != 5:
                track.last_played = datetime.now()

            if i == 1 or i == 3:
                track.play_count = 1000000

    return tracks, random_files


def test_limit_basic():
    tracks = random_tracks(50)

    limiter = ItemLimiter()
    limiter.limit(tracks)
    assert len(tracks) == 50

    limiter = ItemLimiter(on=LimitType.ITEMS)
    limiter.limit(tracks)
    assert len(tracks) == 50


def test_limit_on_items():
    tracks, _ = get_tracks_for_limit_test()

    limiter = ItemLimiter(limit=25)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 25

    limiter = ItemLimiter(limit=10, sorted_by="HighestRating")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 10
    assert set(track.album for track in tracks_copy) == {"album 5"}

    limiter = ItemLimiter(limit=20, sorted_by="most often played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3"}

    limiter = ItemLimiter(limit=20, sorted_by="most often played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy, ignore=[track for track in tracks if track.album == "album 5"])
    assert len(tracks_copy) == 30
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3", "album 5"}


def test_limit_on_albums():
    tracks, _ = get_tracks_for_limit_test()

    limiter = ItemLimiter(limit=3, on=LimitType.ALBUMS)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 30

    limiter = ItemLimiter(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20
    assert set(track.album for track in tracks_copy) == {"album 1", "album 5"}

    limiter = ItemLimiter(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy, ignore={track for track in tracks if track.album == "album 3"})
    assert len(tracks_copy) == 30
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3", "album 5"}


def test_limit_on_seconds():
    tracks, _ = get_tracks_for_limit_test()

    limiter = ItemLimiter(limit=30, on=LimitType.MINUTES)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20

    limiter = ItemLimiter(limit=30, on=LimitType.MINUTES, allowance=2)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 21


def test_limit_on_bytes():
    tracks, random_files = get_tracks_for_limit_test()

    limiter = ItemLimiter(limit=30, on=LimitType.KILOBYTES)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20

    limiter = ItemLimiter(limit=30, on=LimitType.KILOBYTES, allowance=2)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 21

    for path in random_files:
        os.remove(path)
