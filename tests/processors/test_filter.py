from abc import ABCMeta
from os.path import join
from random import sample, shuffle

import pytest
import xmltodict

from syncify.local.track import LocalTrack
from syncify.local.track.field import LocalTrackField
from syncify.processors.compare import Comparer
from syncify.processors.filter import FilterDefinedList, FilterPath, FilterComparers, FilterMatcher, \
    FilterIncludeExclude
from tests.local.playlist.utils import path_playlist_xautopf_bp, path_playlist_xautopf_ra, path_playlist_resources
from tests.local.track.utils import random_tracks
from tests.local.utils import path_track_wma, path_track_flac, path_track_mp3, path_track_resources
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


class TestFilterPath(FilterTester):

    @pytest.fixture
    def obj(self) -> FilterPath:
        return FilterPath(
            values=[f"D:\\exclude\\{random_str(30, 50)}.MP3" for _ in range(20)],
            stem_replacement="/Path/to/LIBRARY/on/linux",
            possible_stems=["../", "D:\\paTh\\on\\Windows"],
            check_existence=False
        )

    def test_init_existence_check(self):
        # none of the random file paths exist, check existence should return empty lists
        replacement_stem = "/Path/to/LIBRARY/on/linux"
        possible_stems = ["../", "D:\\paTh\\on\\Windows"]
        paths = [f"{possible_stems[1]}\\include\\{random_str(30, 50)}.MP3" for _ in range(20)]

        assert not FilterPath(
            paths, stem_replacement=replacement_stem, possible_stems=possible_stems, check_existence=True
        ).ready

    def test_init_stem_replacement(self):
        replacement_stem = "/Path/to/LIBRARY/on/linux"
        possible_stems = ["../", "D:\\paTh\\on\\Windows"]

        paths_0 = [f"{possible_stems[1]}\\include\\{random_str(30, 50)}.MP3" for _ in range(20)]
        filter_0 = FilterPath(
            paths_0, stem_replacement=replacement_stem, possible_stems=possible_stems, check_existence=False
        )

        assert filter_0.stem_original == possible_stems[1].rstrip("/\\")
        assert filter_0.values == [
            path.replace(possible_stems[1], replacement_stem).replace("\\", "/").casefold() for path in paths_0
        ]

        paths_1 = [f"{possible_stems[1]}\\include\\{random_str(30, 50)}.MP3" for _ in range(20)]
        filter_1 = FilterPath(
            paths_1, stem_replacement=replacement_stem, possible_stems=possible_stems, check_existence=False
        )

        assert filter_1.stem_original == possible_stems[1].rstrip("/\\")
        assert filter_1.values == [
            path.replace(possible_stems[1], replacement_stem).replace("\\", "/").casefold() for path in paths_1
        ]

    def test_init_replaces_with_existing_paths(self):
        filter_ = FilterPath(
            values=(path_track_flac.upper(), path_track_mp3.upper()),
            stem_replacement=path_track_resources,
            existing_paths=(path_track_flac, path_track_mp3, path_track_wma),
            check_existence=True
        )
        assert filter_.values == [path_track_flac.casefold(), path_track_mp3.casefold()]

    def test_filter(self):
        replacement_stem = "/Path/to/LIBRARY/on/linux"
        possible_stems = ["../", "D:\\paTh\\on\\Windows"]

        paths = [f"{possible_stems[1]}\\include\\{random_str(30, 50)}.MP3" for _ in range(20)]
        filter_ = FilterPath(
            paths, stem_replacement=replacement_stem, possible_stems=possible_stems, check_existence=False
        )

        expected = [path.replace(possible_stems[1], possible_stems[0]).replace("\\", "/") for path in paths[:10]]
        extra = [f"{possible_stems[0]}/exclude/{random_str(30, 50)}.MP3" for _ in range(13)]
        expected_shuffled = expected.copy()
        shuffle(expected_shuffled)
        assert filter_(expected_shuffled + extra) == expected


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
            include=FilterPath(
                values=[f"{self.library_folder}/include/{random_str(30, 50)}.MP3" for _ in range(20)],
                stem_replacement=self.library_folder,
                check_existence=False
            ),
            exclude=FilterPath(
                values=[f"{self.library_folder}/exclude/{random_str(30, 50)}.MP3" for _ in range(20)],
                stem_replacement=self.library_folder,
                check_existence=False
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

    def test_filter_empty(self, tracks_include: list[LocalTrack], tracks_exclude: list[LocalTrack]):
        assert FilterMatcher().process(values=tracks_include) == tracks_include
        assert FilterMatcher().process(values=tracks_exclude) == tracks_exclude

    def test_filter_no_comparers(
            self, tracks: list[LocalTrack], tracks_include: list[LocalTrack], tracks_exclude: list[LocalTrack],
    ):
        filter_ = FilterMatcher(
            include=FilterPath(tracks_include, check_existence=False),
            exclude=FilterPath(tracks_exclude, check_existence=False),
        )
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
    ):
        filter_ = FilterMatcher(
            comparers=FilterComparers(comparers, match_all=False),
            include=FilterPath(tracks_include, check_existence=False),
            exclude=FilterPath(tracks_exclude, check_existence=False),
        )
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
    ):
        filter_ = FilterMatcher(
            comparers=FilterComparers(comparers, match_all=True),
            include=FilterPath(tracks_include, check_existence=False),
            exclude=FilterPath(tracks_exclude, check_existence=False),
        )
        tracks_artist_reduced = [track for track in tracks_artist if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(filter_(values=tracks), key=self.sort_key)
        assert matches == sorted(tracks_artist_reduced + tracks_include_reduced, key=self.sort_key)

    ###########################################################################
    ## XML I/O
    ###########################################################################
    def test_from_xml_1(self):
        with open(path_playlist_xautopf_bp, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        filter_: FilterMatcher = FilterMatcher.from_xml(
            xml=xml, library_folder=path_resources, other_folders="../", check_existence=False
        )

        include: FilterPath = filter_.include
        exclude: FilterPath = filter_.exclude

        assert len(filter_.comparers.comparers) == 3  # loaded Comparer settings are tested in class-specific tests
        assert filter_.comparers.match_all
        assert include.stem_replacement == path_resources.rstrip("\\/")
        assert include.stem_original == ".."
        assert exclude.stem_replacement == path_resources.rstrip("\\/")
        assert exclude.stem_original == ".."
        assert set(include) == {path_track_wma.casefold(), path_track_mp3.casefold(), path_track_flac.casefold()}
        assert set(exclude) == {
            join(path_playlist_resources,  "exclude_me_2.mp3").casefold(),
            path_track_mp3.casefold(),
            join(path_playlist_resources, "exclude_me.flac").casefold(),
        }

    def test_from_xml_2(self):
        with open(path_playlist_xautopf_ra, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        filter_: FilterMatcher = FilterMatcher.from_xml(
            xml=xml, library_folder=path_resources, other_folders="../", check_existence=False
        )

        include: FilterPath = filter_.include
        exclude: FilterPath = filter_.exclude

        assert len(filter_.comparers.comparers) == 0
        assert not filter_.comparers.match_all
        assert include.stem_replacement == path_resources.rstrip("\\/")
        assert include.stem_original is None
        assert exclude.stem_replacement == path_resources.rstrip("\\/")
        assert exclude.stem_original is None
        assert len(include) == 0
        assert len(exclude) == 0

    @pytest.mark.skip  # TODO: add test for to_xml
    def test_to_xml(self):
        pass
