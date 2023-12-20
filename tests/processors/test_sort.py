from collections.abc import Callable
from itertools import groupby
from random import choice, randrange

import pytest

from syncify.fields import TrackField, LocalTrackField
from syncify.local.track import LocalTrack
from syncify.processors.sort import ItemSorter, ShuffleMode
from syncify.utils.helpers import strip_ignore_words
from tests.abstract.misc import PrettyPrinterTester
from tests.local.utils import random_tracks


# TODO: add test for to_xml

class TestItemSorter(PrettyPrinterTester):

    @staticmethod
    @pytest.fixture
    def obj() -> ItemSorter:
        return ItemSorter(fields=[TrackField.ALBUM, TrackField.DISC, TrackField.TRACK], shuffle_mode=ShuffleMode.NONE)

    @staticmethod
    @pytest.fixture(scope="class")
    def tracks() -> list[LocalTrack]:
        """Generate a list of random tracks with dynamically configured properties for sort tests"""
        tracks = random_tracks(30)
        for i, track in enumerate(tracks, 1):
            track.album = choice(["album 1", "album 2"])
            track.track_number = i
            track.track_total = len(tracks)
            track.disc_number = randrange(1, 3)
            track.date_added = track.date_added.replace(second=i)

        return tracks

    @staticmethod
    def test_sort_by_field_basic(tracks: list[LocalTrack]):
        # no shuffle and reverse
        tracks_original = tracks.copy()
        ItemSorter.sort_by_field(tracks)
        assert tracks == tracks_original
        ItemSorter.sort_by_field(tracks, reverse=True)
        assert tracks == list(reversed(tracks_original))

    @staticmethod
    def test_sort_by_track_number(tracks: list[LocalTrack]):
        tracks_sorted = sorted(tracks, key=lambda t: t.track_number)
        ItemSorter.sort_by_field(tracks, field=TrackField.TRACK)
        assert tracks == tracks_sorted
        ItemSorter.sort_by_field(tracks, field=TrackField.TRACK, reverse=True)
        assert tracks == list(reversed(tracks_sorted))

    @staticmethod
    def test_sort_by_date_added(tracks: list[LocalTrack]):
        tracks_sorted = sorted(tracks, key=lambda t: t.date_added)
        ItemSorter.sort_by_field(tracks, field=LocalTrackField.DATE_ADDED)
        assert tracks == tracks_sorted
        ItemSorter.sort_by_field(tracks, field=LocalTrackField.DATE_ADDED, reverse=True)
        assert tracks == list(reversed(tracks_sorted))

    @staticmethod
    def test_sort_by_title_with_ignore_words(tracks: list[LocalTrack]):
        # sort on str, ignoring defined words like 'The' and 'A'
        tracks_sorted = sorted(tracks, key=lambda t: strip_ignore_words(t.title))
        ItemSorter.sort_by_field(tracks, field=TrackField.TITLE)
        assert tracks == tracks_sorted
        ItemSorter.sort_by_field(tracks, field=TrackField.TITLE, reverse=True)
        assert tracks == list(reversed(tracks_sorted))

    @staticmethod
    def test_group_by_field(tracks: list[LocalTrack]):
        assert ItemSorter.group_by_field(tracks) == {None: tracks}

        groups = ItemSorter.group_by_field(tracks, TrackField.KEY)
        assert sorted(groups) == sorted(set(track.key for track in tracks))
        assert sum(len(t) for t in groups.values()) == len(tracks)

    @staticmethod
    def test_random_shuffle(tracks: list[LocalTrack]):
        tracks_original = tracks.copy()
        ItemSorter().sort(tracks)
        assert tracks == tracks_original
        ItemSorter(shuffle_mode=ShuffleMode.RANDOM).sort(tracks)
        assert tracks != tracks_original
        ItemSorter(fields=TrackField.TITLE, shuffle_mode=ShuffleMode.RANDOM).sort(tracks)
        assert tracks != sorted(tracks, key=lambda t: strip_ignore_words(t.title))

    @staticmethod
    def test_multi_sort(tracks: list[LocalTrack]):
        tracks_sorted = sorted(tracks, key=lambda t: (t.album, t.disc_number, t.track_number))
        sorter = ItemSorter(fields=[TrackField.ALBUM, TrackField.DISC, TrackField.TRACK], shuffle_mode=ShuffleMode.NONE)
        sorter(tracks)
        assert tracks == tracks_sorted

        # complex multi-sort, includes reverse options
        tracks_sorted = []
        sort_key_1: Callable[[LocalTrack], str] = lambda t: t.album
        for _, group_1 in groupby(sorted(tracks, key=sort_key_1, reverse=True), key=sort_key_1):
            sort_key_2: Callable[[LocalTrack], int] = lambda t: t.disc_number
            for __, group_2 in groupby(sorted(group_1, key=sort_key_2), key=sort_key_2):
                sort_key_3: Callable[[LocalTrack], int] = lambda t: t.track_number
                for ___, group_3 in groupby(sorted(group_2, key=sort_key_3, reverse=True), key=sort_key_3):
                    tracks_sorted.extend(list(group_3))

        fields = {TrackField.ALBUM: True, TrackField.DISC: False, TrackField.TRACK: True}
        sorter = ItemSorter(fields=fields, shuffle_mode=ShuffleMode.NONE)
        sorter(tracks)
        assert tracks == tracks_sorted
