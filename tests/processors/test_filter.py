from abc import ABCMeta
from os.path import join
from random import sample, shuffle

import pytest
import xmltodict

from musify.local.file import PathStemMapper, PathMapper
from musify.local.track import LocalTrack
from musify.local.track.field import LocalTrackField
from musify.processors.compare import Comparer
from musify.processors.filter import FilterDefinedList, FilterComparers, FilterIncludeExclude
from musify.processors.filter_matcher import FilterMatcher
from tests.local.playlist.utils import path_playlist_xautopf_bp, path_playlist_xautopf_ra, path_playlist_resources
from tests.local.track.utils import random_tracks
from tests.local.utils import path_track_all, path_track_wma, path_track_flac, path_track_mp3
from tests.shared.core.misc import PrettyPrinterTester
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
        """Yields a list :py:class:`Comparer` objects to be used as pytest.fixture"""
        return [
            Comparer(condition="is", expected="album name", field=LocalTrackField.ALBUM),
            Comparer(condition="starts with", expected="artist", field=LocalTrackField.ARTIST)
        ]

    @pytest.fixture
    def obj(self, comparers: list[Comparer]) -> FilterComparers:
        return FilterComparers(comparers=comparers)

    def test_filter(self, comparers: list[Comparer]):
        tracks = random_tracks(30)
        for track in tracks[:12]:
            track.album = "album name"
        tracks_artist = tracks[10:20]
        for track in tracks_artist:
            track.artist = "artist name"

        assert FilterComparers().process(tracks) == tracks

        filter_ = FilterComparers(comparers=comparers, match_all=False)
        assert filter_(tracks) == tracks[:20]

        filter_ = FilterComparers(comparers=comparers, match_all=True)
        assert filter_(tracks) == tracks[10:12]


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
            comparers=FilterComparers(*comparers),
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
        filter_ = FilterMatcher(
            include=FilterDefinedList([track.path.casefold() for track in tracks_include]),
            exclude=FilterDefinedList([track.path.casefold() for track in tracks_exclude]),
        )
        filter_.include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        filter_.exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        assert filter_(values=tracks) == tracks_include_reduced
        assert filter_.process(values=tracks) == tracks_include_reduced

    def test_filter_on_any_comparers(
            self,
            comparers: list[Comparer],
            tracks: list[LocalTrack],
            tracks_album: list[LocalTrack],
            tracks_include: list[LocalTrack],
            tracks_exclude: list[LocalTrack],
            path_mapper: PathMapper,
    ):
        filter_ = FilterMatcher(
            comparers=FilterComparers(comparers, match_all=False),
            include=FilterDefinedList([track.path.casefold() for track in tracks_include]),
            exclude=FilterDefinedList([track.path.casefold() for track in tracks_exclude]),
        )
        filter_.include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        filter_.exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        tracks_album_reduced = [track for track in tracks_album if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(filter_(values=tracks), key=self.sort_key)
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
        filter_ = FilterMatcher(
            comparers=FilterComparers(comparers, match_all=True),
            include=FilterDefinedList([track.path.casefold() for track in tracks_include]),
            exclude=FilterDefinedList([track.path.casefold() for track in tracks_exclude]),
        )
        filter_.include.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        filter_.exclude.transform = lambda x: path_mapper.map(x, check_existence=False).casefold()
        tracks_artist_reduced = [track for track in tracks_artist if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(filter_(values=tracks), key=self.sort_key)
        assert matches == sorted(tracks_artist_reduced + tracks_include_reduced, key=self.sort_key)

    ###########################################################################
    ## XML I/O
    ###########################################################################
    def test_from_xml_1(self, path_mapper: PathStemMapper):
        with open(path_playlist_xautopf_bp, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        filter_: FilterMatcher = FilterMatcher.from_xml(xml=xml, path_mapper=path_mapper)

        assert len(filter_.comparers.comparers) == 3  # loaded Comparer settings are tested in class-specific tests
        assert filter_.comparers.match_all
        assert set(filter_.include) == {
            path_track_wma.casefold(), path_track_mp3.casefold(), path_track_flac.casefold()
        }
        assert set(filter_.exclude) == {
            join(path_playlist_resources,  "exclude_me_2.mp3").casefold(),
            path_track_mp3.casefold(),
            join(path_playlist_resources, "exclude_me.flac").casefold(),
        }

    def test_from_xml_2(self, path_mapper: PathStemMapper):
        with open(path_playlist_xautopf_ra, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        filter_: FilterMatcher = FilterMatcher.from_xml(xml=xml, path_mapper=path_mapper)

        assert len(filter_.comparers.comparers) == 0
        assert not filter_.comparers.match_all
        assert len(filter_.include) == 0
        assert len(filter_.exclude) == 0

    @pytest.mark.skip(reason="not implemented yet")
    def test_to_xml(self):
        pass
