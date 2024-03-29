from abc import ABCMeta
from collections.abc import Mapping
from os.path import join
from random import sample, shuffle, randrange

import pytest
import xmltodict

from musify.libraries.local.track import LocalTrack
from musify.libraries.local.track.field import LocalTrackField
from musify.processors.compare import Comparer
from musify.processors.filter import FilterDefinedList, FilterComparers, FilterIncludeExclude
from musify.processors.filter_matcher import FilterMatcher
from musify.core.enum import Fields
from musify.file.path_mapper import PathStemMapper, PathMapper
from tests.libraries.local.track.utils import random_tracks
from tests.libraries.local.utils import path_playlist_resources
from tests.libraries.local.utils import path_playlist_xautopf_bp, path_playlist_xautopf_ra, path_playlist_xautopf_cm
from tests.libraries.local.utils import path_track_all, path_track_wma, path_track_flac, path_track_mp3
from tests.core.printer import PrettyPrinterTester
from tests.utils import random_str, path_resources


class FilterTester(PrettyPrinterTester, metaclass=ABCMeta):
    pass


class TestFilterDefinedList(FilterTester):

    @pytest.fixture
    def obj(self) -> FilterDefinedList:
        return FilterDefinedList(values=[random_str(30, 50) for _ in range(20)])

    def test_filter(self):
        values = [random_str(30, 50) for _ in range(20)]

        assert FilterDefinedList().process(values) == values

        expected = values
        expected_shuffled = expected.copy()
        shuffle(expected_shuffled)
        filter_ = FilterDefinedList(values=values)
        assert filter_(values[:10]) == values[:10]


class TestFilterComparers(FilterTester):

    @pytest.fixture(scope="class")
    def comparers(self) -> list[Comparer]:
        """Yields a list of :py:class:`Comparer` objects to be used as pytest.fixture"""
        return [
            Comparer(condition="is", expected="album name", field=LocalTrackField.ALBUM),
            Comparer(condition="starts with", expected="artist", field=LocalTrackField.ARTIST)
        ]

    @pytest.fixture
    def obj(self, comparers: list[Comparer]) -> FilterComparers:
        return FilterComparers(comparers=comparers)

    @pytest.fixture
    def tracks(self) -> list[LocalTrack]:
        """
        Yields a list of :py:class:`LocalTrack` objects that match the comparers fixtures
        to be used as pytest.fixture
        """
        tracks = random_tracks(30)
        for track in tracks[:18]:
            track.album = "album name"

        tracks_artist = tracks[10:25]
        for track in tracks_artist:
            track.artist = "artist name"

        return tracks

    def test_filter(self, comparers: list[Comparer], tracks: list[LocalTrack]):
        assert FilterComparers().process(tracks) == tracks

        comparer = FilterComparers(comparers=comparers, match_all=False)
        assert comparer(tracks) == tracks[:25]

        comparer = FilterComparers(comparers=comparers, match_all=True)
        assert comparer(tracks) == tracks[10:18]

    def test_filter_nested(self, comparers: list[Comparer], tracks: list[LocalTrack]):
        sub_filter_1 = FilterComparers(
            comparers=[
                Comparer(condition="is", expected=2020, field=LocalTrackField.YEAR),
                Comparer(condition="in range", expected=[80, 100], field=LocalTrackField.BPM)
            ],
            match_all=False
        )
        sub_filter_2 = FilterComparers(
            comparers=[
                Comparer(condition="greater than", expected=20, field=LocalTrackField.TRACK_NUMBER)
            ],
            match_all=True
        )

        for i, track in enumerate(tracks):
            track.track_number = i + 1
            track.year = 2020 if i >= 8 else 1990
            track.bpm = randrange(85, 95) if 10 < i < 15 else 120

        comparer = FilterComparers(
            comparers={comparers[0]: (False, sub_filter_1), comparers[1]: (False, sub_filter_2)},
            match_all=False
        )
        assert sorted(comparer(tracks), key=lambda x: x.track_number) == tracks  # loose conditions, matches everything

        comparer = FilterComparers(
            comparers={comparers[0]: (True, sub_filter_1), comparers[1]: (False, sub_filter_2)},
            match_all=False
        )
        assert sorted(comparer(tracks), key=lambda x: x.track_number) == tracks[8:]

        sub_filter_1.match_all = True
        comparer = FilterComparers(
            comparers={comparers[0]: (True, sub_filter_1), comparers[1]: (False, sub_filter_2)},
            match_all=False
        )
        assert sorted(comparer(tracks), key=lambda x: x.track_number) == tracks[10:]

        comparer = FilterComparers(
            comparers={comparers[0]: (True, sub_filter_1), comparers[1]: (True, sub_filter_2)},
            match_all=False
        )
        assert sorted(comparer(tracks), key=lambda x: x.track_number) == tracks[11:15] + tracks[20:25]

        comparer = FilterComparers(
            comparers={comparers[0]: (True, sub_filter_1), comparers[1]: (True, sub_filter_2)},
            match_all=True
        )
        assert not comparer(tracks)  # no overlap between the 2 parent comparers


class TestFilterIncludeExclude(FilterTester):

    @pytest.fixture
    def obj(self) -> FilterIncludeExclude:
        include_values = [random_str(30, 50) for _ in range(20)]
        return FilterIncludeExclude(
            include=FilterDefinedList(include_values),
            exclude=FilterDefinedList(include_values[:10] + [random_str(30, 50) for _ in range(20)]),
        )

    def test_filter(self, obj: FilterIncludeExclude):
        assert obj(obj.include.values) == obj.include.values[10:20]
        assert not obj(obj.exclude.values)


class TestFilterMatcher(FilterTester):

    library_folder = "/path/to/library"

    @pytest.fixture(scope="class")
    def comparers(self) -> list[Comparer]:
        """Yields a list :py:class:`Comparer` objects to be used as pytest.fixture"""
        return [
            Comparer(condition="is", expected="album name", field=LocalTrackField.ALBUM),
            Comparer(condition="starts with", expected="artist", field=LocalTrackField.ARTIST)
        ]

    @pytest.fixture
    def obj(self, comparers: list[Comparer]) -> FilterMatcher:
        return FilterMatcher(
            comparers=FilterComparers(comparers),
            include=FilterDefinedList(
                [f"{self.library_folder}/include/{random_str(30, 50)}.MP3" for _ in range(20)],
            ),
            exclude=FilterDefinedList(
                [f"{self.library_folder}/exclude/{random_str(30, 50)}.MP3" for _ in range(20)],
            ),
        )

    @staticmethod
    def sort_key(track: LocalTrack) -> str:
        """The key to sort on when making assertions in tests"""
        return track.path

    @pytest.fixture(scope="class")
    def tracks(self) -> list[LocalTrack]:
        """Yield a list of random LocalTracks to use for testing the :py:class:`LocalMatcher`"""
        tracks = random_tracks(30)
        return tracks

    @pytest.fixture(scope="class")
    def tracks_album(self, tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the same album name for all these tracks"""
        tracks_album = sample(tracks, 15)
        for track in tracks_album:
            track.album = "album name"
        return tracks_album

    @pytest.fixture(scope="class")
    def tracks_artist(self, tracks_album: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the same artist name for all these tracks"""
        tracks_artist = sample(tracks_album, 9)
        for track in tracks_artist:
            track.artist = "artist name"
        return tracks_artist

    @pytest.fixture(scope="class")
    def tracks_include(self, tracks: list[LocalTrack], tracks_album: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the path to be included for all these tracks"""
        include_paths = [f"{self.library_folder}/include/{random_str(30, 50)}.MP3" for _ in range(20)]
        tracks_include = sample([track for track in tracks if track not in tracks_album], 7)

        for i, track in enumerate(tracks_include):
            track._path = include_paths[i]
        return tracks_include

    @pytest.fixture(scope="class")
    def tracks_exclude(self, tracks_artist: list[LocalTrack], tracks_include: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the path to be excluded for all these tracks"""
        exclude_paths = [f"{self.library_folder}/exclude/{random_str(30, 50)}.MP3" for _ in range(20)]
        tracks_exclude = sample(tracks_artist, 3) + sample(tracks_include, 2)

        for i, track in enumerate(tracks_exclude):
            track._path = exclude_paths[i]
        return tracks_exclude

    @pytest.fixture(scope="class")
    def path_mapper(self) -> PathStemMapper:
        """Yields a :py:class:`PathMapper` that can map paths from the test playlist files"""
        yield PathStemMapper(stem_map={"../": path_resources}, available_paths=path_track_all)

    def test_filter_empty(self, tracks_include: list[LocalTrack], tracks_exclude: list[LocalTrack]):
        assert FilterMatcher().process(values=tracks_include) == tracks_include
        assert FilterMatcher().process(values=tracks_exclude) == tracks_exclude

    def test_filter_no_comparers(
            self,
            tracks: list[LocalTrack],
            tracks_include: list[LocalTrack],
            tracks_exclude: list[LocalTrack],
            path_mapper: PathMapper
    ):
        matcher = FilterMatcher(
            include=FilterDefinedList([track.path.casefold() for track in tracks_include]),
            exclude=FilterDefinedList([track.path.casefold() for track in tracks_exclude]),
        )
        matcher.include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        matcher.exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        assert matcher(values=tracks) == tracks_include_reduced
        assert matcher.process(values=tracks) == tracks_include_reduced

    def test_filter_on_any_comparers(
            self,
            comparers: list[Comparer],
            tracks: list[LocalTrack],
            tracks_album: list[LocalTrack],
            tracks_include: list[LocalTrack],
            tracks_exclude: list[LocalTrack],
            path_mapper: PathMapper,
    ):
        matcher = FilterMatcher(
            comparers=FilterComparers(comparers, match_all=False),
            include=FilterDefinedList([track.path.casefold() for track in tracks_include]),
            exclude=FilterDefinedList([track.path.casefold() for track in tracks_exclude]),
        )
        matcher.include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        matcher.exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        tracks_album_reduced = [track for track in tracks_album if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(matcher(values=tracks), key=self.sort_key)
        assert matches == sorted(tracks_album_reduced + tracks_include_reduced, key=self.sort_key)

    def test_filter_on_all_comparers(
            self,
            comparers: list[Comparer],
            tracks: list[LocalTrack],
            tracks_album: list[LocalTrack],
            tracks_artist: list[LocalTrack],
            tracks_include: list[LocalTrack],
            tracks_exclude: list[LocalTrack],
            path_mapper: PathMapper,
    ):
        matcher = FilterMatcher(
            comparers=FilterComparers(comparers, match_all=True),
            include=FilterDefinedList([track.path.casefold() for track in tracks_include]),
            exclude=FilterDefinedList([track.path.casefold() for track in tracks_exclude]),
        )
        matcher.include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        matcher.exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()

        tracks_artist_reduced = [track for track in tracks_artist if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(matcher(values=tracks), key=self.sort_key)
        assert matches == sorted(tracks_artist_reduced + tracks_include_reduced, key=self.sort_key)

    ###########################################################################
    ## XML I/O
    ###########################################################################
    def test_from_xml_bp(self, path_mapper: PathStemMapper):
        with open(path_playlist_xautopf_bp, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        matcher = FilterMatcher.from_xml(xml=xml, path_mapper=path_mapper)

        assert set(matcher.include) == {
            path_track_wma.casefold(), path_track_mp3.casefold(), path_track_flac.casefold()
        }
        assert set(matcher.exclude) == {
            join(path_playlist_resources,  "exclude_me_2.mp3").casefold(),
            path_track_mp3.casefold(),
            join(path_playlist_resources, "exclude_me.flac").casefold(),
        }

        assert isinstance(matcher.comparers.comparers, dict)
        assert len(matcher.comparers.comparers) == 3  # loaded Comparer settings are tested in class-specific tests
        assert matcher.comparers.match_all
        assert all(not m[1].ready for m in matcher.comparers.comparers.values())

    def test_from_xml_ra(self, path_mapper: PathStemMapper):
        with open(path_playlist_xautopf_ra, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        matcher = FilterMatcher.from_xml(xml=xml, path_mapper=path_mapper)

        assert len(matcher.include) == 0
        assert len(matcher.exclude) == 0

        assert isinstance(matcher.comparers.comparers, dict)
        assert len(matcher.comparers.comparers) == 0
        assert not matcher.comparers.match_all
        assert all(not m[1].ready for m in matcher.comparers.comparers.values())

    def test_from_xml_cm(self, path_mapper: PathStemMapper):
        with open(path_playlist_xautopf_cm, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        matcher = FilterMatcher.from_xml(xml=xml, path_mapper=path_mapper)

        assert isinstance(matcher.comparers.comparers, Mapping)
        assert len(matcher.comparers.comparers) == 3
        assert not matcher.comparers.match_all

        # assertions on parent comparers
        comparers: list[Comparer] = list(matcher.comparers.comparers)
        assert comparers[0].field == Fields.ALBUM
        assert comparers[0].condition == "contains"
        assert comparers[0].expected == ["an album"]
        assert comparers[1].field == Fields.RATING
        assert comparers[1].condition == "in_range"
        assert comparers[1].expected == ["40", "80"]
        assert comparers[2].field == Fields.YEAR
        assert comparers[2].condition == "is"
        assert comparers[2].expected == ["2024"]

        # assertions on child comparers
        sub_filters: list[tuple[bool, FilterComparers]] = list(matcher.comparers.comparers.values())
        assert not sub_filters[0][1].ready
        assert not sub_filters[0][0]  # And/Or condition

        sub_filter_1 = sub_filters[1][1]
        assert sub_filter_1.ready
        assert not sub_filter_1.match_all
        assert isinstance(sub_filter_1.comparers, Mapping)
        assert all(not m[1].ready for m in sub_filter_1.comparers.values())
        assert sub_filters[1][0]  # And/Or condition

        sub_comparers_1: list[Comparer] = list(sub_filters[1][1].comparers)
        assert sub_comparers_1[0].field == Fields.GENRES
        assert sub_comparers_1[0].condition == "is_in"
        assert sub_comparers_1[0].expected == ["Jazz", "Rock", "Pop"]
        assert sub_comparers_1[1].field == Fields.TRACK_NUMBER
        assert sub_comparers_1[1].condition == "less_than"
        assert sub_comparers_1[1].expected == ["50"]

        sub_filter_2 = sub_filters[2][1]
        assert sub_filter_2.ready
        assert sub_filter_2.match_all
        assert isinstance(sub_filter_2.comparers, Mapping)
        assert all(not m[1].ready for m in sub_filter_2.comparers.values())
        assert not sub_filters[2][0]  # And/Or condition

        sub_comparers_2: list[Comparer] = list(sub_filter_2.comparers)
        assert sub_comparers_2[0].field == Fields.ARTIST
        assert sub_comparers_2[0].condition == "starts_with"
        assert sub_comparers_2[0].expected == ["an artist"]
        assert sub_comparers_2[1].field == Fields.LAST_PLAYED
        assert sub_comparers_2[1].condition == "in_the_last"
        assert sub_comparers_2[1].expected == ["7d"]

    @pytest.mark.skip(reason="not implemented yet")
    def test_to_xml(self):
        pass
