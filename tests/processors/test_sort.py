from collections.abc import Callable
from itertools import groupby
from random import choice, randrange

import pytest

from musify.field import TrackField
from musify.libraries.local.track import LocalTrack
from musify.libraries.local.track.field import LocalTrackField
from musify.processors.sort import ItemSorter, ShuffleMode
from musify.utils import strip_ignore_words
from tests.core.printer import PrettyPrinterTester
from tests.libraries.local.track.utils import random_tracks


class TestItemSorter(PrettyPrinterTester):

    @pytest.fixture
    def obj(self) -> ItemSorter:
        return ItemSorter(fields=[TrackField.ALBUM, TrackField.DISC, TrackField.TRACK])

    @pytest.fixture(scope="class")
    def tracks(self) -> list[LocalTrack]:
        """Generate a list of random tracks with dynamically configured properties for sort tests"""
        tracks = random_tracks(30)
        for i, track in enumerate(tracks, 1):
            track.album = choice(["album 1", "album 2"])
            track.track_number = i
            track.track_total = len(tracks)
            track.disc_number = randrange(1, 3)
            track.date_added = track.date_added.replace(second=i)

        return tracks

    def test_sort_by_field_basic(self, tracks: list[LocalTrack]):
        # no shuffle and reverse
        tracks_original = tracks.copy()
        ItemSorter.sort_by_field(tracks)
        assert tracks == tracks_original
        ItemSorter.sort_by_field(tracks, reverse=True)
        assert tracks == list(reversed(tracks_original))

    def test_sort_by_track_number(self, tracks: list[LocalTrack]):
        tracks_sorted = sorted(tracks, key=lambda t: t.track_number)
        ItemSorter.sort_by_field(tracks, field=TrackField.TRACK)
        assert tracks == tracks_sorted
        ItemSorter.sort_by_field(tracks, field=TrackField.TRACK, reverse=True)
        assert tracks == list(reversed(tracks_sorted))

    def test_sort_by_date_added(self, tracks: list[LocalTrack]):
        tracks_sorted = sorted(tracks, key=lambda t: t.date_added)
        ItemSorter.sort_by_field(tracks, field=LocalTrackField.DATE_ADDED)
        assert tracks == tracks_sorted
        ItemSorter.sort_by_field(tracks, field=LocalTrackField.DATE_ADDED, reverse=True)
        assert tracks == list(reversed(tracks_sorted))

    def test_sort_by_title_with_ignore_words(self, tracks: list[LocalTrack]):
        # sort on str, ignoring defined words like 'The' and 'A'
        tracks_sorted = sorted(tracks, key=lambda t: strip_ignore_words(t.title))
        ItemSorter.sort_by_field(tracks, field=TrackField.TITLE)
        assert tracks == tracks_sorted
        ItemSorter.sort_by_field(tracks, field=TrackField.TITLE, reverse=True)
        assert tracks == list(reversed(tracks_sorted))

    def test_group_by_field(self, tracks: list[LocalTrack]):
        assert ItemSorter.group_by_field(tracks) == {None: tracks}

        groups = ItemSorter.group_by_field(tracks, TrackField.KEY)
        assert sorted(groups) == sorted(set(track.key for track in tracks))
        assert sum(len(t) for t in groups.values()) == len(tracks)

    def test_random_shuffle(self, tracks: list[LocalTrack]):
        tracks_original = tracks.copy()
        ItemSorter().sort(tracks)
        assert tracks == tracks_original
        ItemSorter(shuffle_mode=ShuffleMode.RANDOM).sort(tracks)
        assert tracks != tracks_original

        # shuffle settings ignored when ``fields`` are defined
        ItemSorter(fields=TrackField.TITLE, shuffle_mode=ShuffleMode.RANDOM).sort(tracks)
        assert tracks == sorted(tracks, key=lambda t: strip_ignore_words(t.title))

    def test_multi_sort(self, tracks: list[LocalTrack]):
        tracks_sorted = sorted(tracks, key=lambda t: (t.album, t.disc_number, t.track_number))
        sorter = ItemSorter(fields=[TrackField.ALBUM, TrackField.DISC, TrackField.TRACK])
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
        sorter = ItemSorter(fields=fields)
        sorter(tracks)
        assert tracks == tracks_sorted
