from random import sample, choice, randrange
from typing import Any, Callable

from syncify.local.files.track import Track, PropertyName
from syncify.local.files.track.collection.sort import ShuffleMode
from syncify.local.files.track import TrackSort, TagName
from tests.common import random_str
from tests.local.files.track.track import random_tracks
from utils_new.generic import strip_ignore_words

from itertools import groupby


def test_sort_by_field():
    tracks = random_tracks(30)
    # print([track.track_number for track in tracks])

    # random shuffle
    tracks_copy = tracks.copy()
    TrackSort.sort_by_field(tracks)
    assert tracks != tracks_copy

    # sort on int
    for i, track in enumerate(tracks, 1):
        track.track_number = i
        track.track_total = len(tracks)

    tracks_sorted = sorted(tracks, key=lambda x: x.track_number)
    TrackSort.sort_by_field(tracks, field=TagName.TRACK)
    assert tracks == tracks_sorted
    TrackSort.sort_by_field(tracks, field=TagName.TRACK, reverse=True)
    assert tracks == list(reversed(tracks_sorted))

    # sort on datetime
    for i, track in enumerate(tracks, 1):
        track.date_modified = track.date_modified.replace(second=i)

    tracks_sorted = sorted(tracks, key=lambda x: x.date_modified)
    TrackSort.sort_by_field(tracks, field=PropertyName.DATE_MODIFIED)
    assert tracks == tracks_sorted
    TrackSort.sort_by_field(tracks, field=PropertyName.DATE_MODIFIED, reverse=True)
    assert tracks == list(reversed(tracks_sorted))

    # sort on str, ignoring defined words like 'The' and 'A'
    tracks_sorted = sorted(tracks, key=lambda x: strip_ignore_words(x.title))
    TrackSort.sort_by_field(tracks, field=TagName.TITLE)
    assert tracks == tracks_sorted
    TrackSort.sort_by_field(tracks, field=TagName.TITLE, reverse=True)
    assert tracks == list(reversed(tracks_sorted))


def test_group_by_field():
    tracks = random_tracks(30)

    assert TrackSort.group_by_field(tracks) == {None: tracks}

    groups = TrackSort.group_by_field(tracks, TagName.KEY)
    assert sorted(groups) == sorted(set(track.key for track in tracks))
    assert sum(len(t) for t in groups.values()) == len(tracks)


def test_sort():
    tracks = random_tracks(30)
    for i, track in enumerate(tracks, 1):
        track.track_number = i
        track.track_total = len(tracks)

    # random shuffle
    tracks_copy = tracks.copy()
    TrackSort(shuffle_mode=ShuffleMode.NONE).sort(tracks)
    assert tracks != tracks_copy
    TrackSort(fields=TagName.TITLE, shuffle_mode=ShuffleMode.RANDOM).sort(tracks)
    assert tracks != tracks_copy

    # prepare tracks
    for track in tracks:
        track.album = choice(["album 1", "album 2"])
        track.disc_number = randrange(1, 3)

    # simple multi-sort

    # for track in tracks_sorted:
    #     print(track.album, track.disc_number, track.track_number)
    # print()

    tracks_sorted = sorted(tracks, key=lambda x: (x.album, x.disc_number, x.track_number))
    TrackSort(fields=[TagName.ALBUM, TagName.DISC, TagName.TRACK], shuffle_mode=ShuffleMode.NONE).sort(tracks)
    assert tracks == tracks_sorted

    # complex multi-sort, includes reverse options
    tracks_sorted = []
    sort_key_1 = lambda x: x.album
    for _, group_1 in groupby(sorted(tracks, key=sort_key_1, reverse=True), key=sort_key_1):
        sort_key_2 = lambda x: x.disc_number
        for __, group_2 in groupby(sorted(group_1, key=sort_key_2), key=sort_key_2):
            sort_key_3 = lambda x: x.track_number
            for ___, group_3 in groupby(sorted(group_2, key=sort_key_3, reverse=True), key=sort_key_3):
                tracks_sorted.extend(list(group_3))
    print("HERE WE GO")
    fields = {TagName.ALBUM: True, TagName.DISC: False, TagName.TRACK: True}
    TrackSort(fields=fields, shuffle_mode=ShuffleMode.NONE).sort(tracks)
    assert tracks == tracks_sorted
