import os
from copy import copy
from datetime import datetime

from tests.common import random_file
from tests.local.track.track import random_tracks

from syncify.local.playlist.processor.limit import TrackLimiter, LimitType


def test_init():
    limiter = TrackLimiter(sorted_by="HighestRating")
    assert limiter._sort_method == limiter._sort_highest_rating

    limiter = TrackLimiter(sorted_by="__ least_ recently_  added __ ")
    assert limiter._sort_method == limiter._sort_least_recently_added

    limiter = TrackLimiter(sorted_by="__most recently played__")
    assert limiter._sort_method == limiter._sort_most_recently_played


def test_limit():
    tracks = random_tracks(50)

    limiter = TrackLimiter()
    limiter.limit(tracks)
    assert len(tracks) == 50

    limiter = TrackLimiter(on=LimitType.ITEMS)
    limiter.limit(tracks)
    assert len(tracks) == 50

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

    # on items
    limiter = TrackLimiter(limit=25)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 25

    limiter = TrackLimiter(limit=10, sorted_by="HighestRating")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 10
    assert set(track.album for track in tracks_copy) == {"album 5"}

    limiter = TrackLimiter(limit=20, sorted_by="most often played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3"}

    limiter = TrackLimiter(limit=20, sorted_by="most often played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy, ignore=[track for track in tracks if track.album == "album 5"])
    assert len(tracks_copy) == 30
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3", "album 5"}

    # on albums
    limiter = TrackLimiter(limit=3, on=LimitType.ALBUMS)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 30

    limiter = TrackLimiter(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20
    assert set(track.album for track in tracks_copy) == {"album 1", "album 5"}

    limiter = TrackLimiter(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy, ignore=[track.path for track in tracks if track.album == "album 3"])
    assert len(tracks_copy) == 30
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3", "album 5"}

    # on seconds
    limiter = TrackLimiter(limit=30, on=LimitType.MINUTES)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20

    limiter = TrackLimiter(limit=30, on=LimitType.MINUTES, allowance=2)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 21

    # on bytes
    limiter = TrackLimiter(limit=30, on=LimitType.KILOBYTES)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20

    limiter = TrackLimiter(limit=30, on=LimitType.KILOBYTES, allowance=2)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 21

    for path in random_files:
        os.remove(path)
