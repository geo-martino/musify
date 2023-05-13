from copy import copy
from datetime import datetime

from syncify.local.playlist.processor import TrackLimit, LimitType
from tests.local.track.track import random_tracks


def test_init():
    limiter = TrackLimit(sorted_by="HighestRating")
    assert limiter._sort_method == limiter._sort_highest_rating

    limiter = TrackLimit(sorted_by="__ least_ recently_  added __ ")
    assert limiter._sort_method == limiter._sort_least_recently_added

    limiter = TrackLimit(sorted_by="__most recently played__")
    assert limiter._sort_method == limiter._sort_most_recently_played


def test_limit():
    tracks = random_tracks(50)

    limiter = TrackLimit()
    limiter.limit(tracks)
    assert len(tracks) == 50

    limiter = TrackLimit(on=LimitType.ITEMS)
    limiter.limit(tracks)
    assert len(tracks) == 50

    # prepare tracks for tests
    tracks = random_tracks(50)
    for i in range(1, 6):
        for track in tracks[(i-1)*10:i*10]:
            track.album = f"album {i}"
            track.length = i * 60
            track.size = i * 1000000
            track.rating = i

            if i != 1 and i != 5:
                track.last_played = datetime.now()

            if i == 1 or i == 3:
                track.play_count = 1000000

    # on items
    limiter = TrackLimit(limit=25)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 25

    limiter = TrackLimit(limit=10, sorted_by="HighestRating")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 10
    assert set(track.album for track in tracks_copy) == {"album 5"}

    limiter = TrackLimit(limit=20, sorted_by="most often played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3"}

    limiter = TrackLimit(limit=20, sorted_by="most often played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy, ignore=[track for track in tracks if track.album == "album 5"])
    assert len(tracks_copy) == 30
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3", "album 5"}

    # on albums
    limiter = TrackLimit(limit=3, on=LimitType.ALBUMS)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 30

    limiter = TrackLimit(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20
    assert set(track.album for track in tracks_copy) == {"album 1", "album 5"}

    limiter = TrackLimit(limit=2, on=LimitType.ALBUMS, sorted_by="least recently played")
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy, ignore=[track.path for track in tracks if track.album == "album 3"])
    assert len(tracks_copy) == 30
    assert set(track.album for track in tracks_copy) == {"album 1", "album 3", "album 5"}

    # on seconds
    limiter = TrackLimit(limit=30, on=LimitType.MINUTES)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20

    limiter = TrackLimit(limit=30, on=LimitType.MINUTES, allowance=2)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 21

    # on bytes
    limiter = TrackLimit(limit=30, on=LimitType.MEGABYTES)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 20

    limiter = TrackLimit(limit=30, on=LimitType.MEGABYTES, allowance=2)
    tracks_copy = copy(tracks)
    limiter.limit(tracks_copy)
    assert len(tracks_copy) == 21
