from datetime import datetime, date, timedelta

import pytest

from syncify.enums.tags import TagName, PropertyName
from syncify.processor.exception import ItemComparerError, ProcessorLookupError
from syncify.processor.compare import ItemComparer
from syncify.local.track import MP3, M4A, FLAC
from tests.local.track.common import random_track


def test_init():
    comparer = ItemComparer(field=TagName.IMAGES, condition="Contains")
    assert comparer.field == TagName.IMAGES
    assert comparer._expected is None
    assert not comparer._converted
    assert comparer.condition == "contains"
    assert comparer._processor == comparer._contains

    comparer = ItemComparer(field=PropertyName.DATE_ADDED, condition="___greater than_  ")
    assert comparer.field == PropertyName.DATE_ADDED
    assert not comparer._converted
    assert comparer._expected is None
    assert comparer.condition == "greater_than"
    assert comparer._processor == comparer._is_after

    comparer = ItemComparer(field=PropertyName.EXT, condition=" is  _", expected=[".mp3", ".flac"])
    assert comparer.field == PropertyName.EXT
    assert not comparer._converted
    assert comparer._expected == [".mp3", ".flac"]
    assert comparer.condition == "is"
    assert comparer._processor == comparer._is

    with pytest.raises(ProcessorLookupError):
        ItemComparer(field=PropertyName.EXT, condition="this cond does not exist")


def test_compare_with_reference():
    track_1 = random_track()
    track_2 = random_track()

    comparer = ItemComparer(field=TagName.ALBUM, condition="StartsWith")
    assert comparer._expected is None
    assert not comparer._converted

    with pytest.raises(ItemComparerError):
        comparer.compare(track=track_1)

    track_1.album = "album 124 is a great album"
    track_2.album = "album"
    assert comparer.compare(track=track_1, reference=track_2)
    assert comparer._expected is None
    assert not comparer._converted

    with pytest.raises(ItemComparerError):
        comparer.compare(track=track_1)


def test_compare_str():
    track = random_track(MP3)

    # no expected values conversion
    comparer = ItemComparer(field=PropertyName.EXT, condition=" is  _", expected=[".mp3", ".flac"])
    assert comparer._expected == [".mp3", ".flac"]
    assert comparer._processor == comparer._is

    assert track.ext == ".mp3"
    assert comparer.compare(track)
    assert comparer._expected == [".mp3", ".flac"]
    assert not comparer.compare(random_track(FLAC))
    assert not comparer.compare(random_track(M4A))


def test_compare_int():
    track = random_track()

    comparer = ItemComparer(field=TagName.TRACK, condition="is in", expected=["1", 2, "3"])
    assert comparer._expected == ["1", 2, "3"]
    assert not comparer._converted
    assert comparer._processor == comparer._is_in

    track.track_number = 3
    assert comparer.compare(track)
    assert comparer._expected == [1, 2, 3]
    assert comparer._converted

    track.track_number = 4
    assert not comparer.compare(track)
    assert comparer._expected == [1, 2, 3]
    assert comparer._converted

    # int: conversion when given a time str
    comparer = ItemComparer(field=PropertyName.RATING, condition="greater than", expected="1:30,618")
    assert comparer._expected == ["1:30,618"]
    assert not comparer._converted
    assert comparer._processor == comparer._is_after

    track.rating = 120
    assert comparer.compare(track)
    assert comparer._expected == [90]
    assert comparer._converted
    track.rating = 60
    assert not comparer.compare(track)
    assert comparer._expected == [90]
    assert comparer._converted


def test_compare_float():
    track = random_track()

    # float
    comparer = ItemComparer(field=TagName.BPM, condition="in_range", expected=["81.96", 100.23])
    assert comparer._expected == ["81.96", 100.23]
    assert not comparer._converted
    assert comparer._processor == comparer._in_range

    track.bpm = 90.0
    assert comparer.compare(track)
    assert comparer._expected == [81.96, 100.23]
    assert comparer._converted

    # does not convert again when giving a value of a different type
    track.bpm = 120
    assert not comparer.compare(track)
    assert comparer._expected == [81.96, 100.23]
    assert comparer._converted


def test_compare_date():
    track = random_track()

    # all datetime comparisons only consider date part
    comparer = ItemComparer(field=PropertyName.DATE_ADDED, condition="is", expected=datetime(2023, 4, 21, 19, 20))
    assert comparer._expected == [datetime(2023, 4, 21, 19, 20)]
    assert not comparer._converted
    assert comparer._processor == comparer._is

    track.date_added = datetime(2023, 4, 21, 11, 30, 49, 203)
    assert comparer.compare(track)
    assert comparer._expected == [date(2023, 4, 21)]
    assert comparer._converted

    # converts supported strings
    comparer = ItemComparer(field=PropertyName.DATE_ADDED, condition="is_not", expected="20/01/01")
    assert comparer._expected == ["20/01/01"]
    assert not comparer._converted
    assert comparer._processor == comparer._is_not

    assert comparer.compare(track)
    assert comparer._expected == [date(2001, 1, 20)]
    assert comparer._converted

    comparer = ItemComparer(field=PropertyName.DATE_ADDED, condition="is_not", expected="13/8/2004")
    assert comparer._expected == ["13/8/2004"]
    assert not comparer._converted
    assert comparer._processor == comparer._is_not

    assert comparer.compare(track)
    assert comparer._expected == [date(2004, 8, 13)]
    assert comparer._converted

    # converts date ranges
    comparer = ItemComparer(field=PropertyName.DATE_ADDED, condition="is_in_the_last", expected="8h")
    assert comparer._expected == ["8h"]
    assert not comparer._converted
    assert comparer._processor == comparer._is_after

    track.date_added = datetime.now() - timedelta(hours=4)
    assert comparer.compare(track)
    # truncate to avoid time lag between assignment and test making the test fail
    exp_truncated = comparer._expected[0].replace(second=0, microsecond=0)
    test_truncated = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=8)
    assert exp_truncated == test_truncated
    assert comparer._converted
