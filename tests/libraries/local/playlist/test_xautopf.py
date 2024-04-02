import os
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from glob import glob
from os.path import dirname, join, splitext, basename, exists
from pathlib import Path
from random import randrange

import pytest

from core.printer import PrettyPrinterTester
from musify.core.enum import Fields
from musify.file.exception import InvalidFileType
from musify.file.path_mapper import PathMapper, PathStemMapper
from musify.libraries.local.library import MusicBee, LocalLibrary
from musify.libraries.local.playlist import XAutoPF
from musify.libraries.local.playlist.xautopf import XMLPlaylistParser
from musify.libraries.local.track import LocalTrack
from musify.libraries.local.track.field import LocalTrackField
from musify.processors.compare import Comparer
from musify.processors.filter import FilterComparers
from musify.processors.limit import LimitType
from musify.processors.sort import ShuffleMode
from musify.utils import to_collection
from tests.libraries.local.playlist.testers import LocalPlaylistTester
from tests.libraries.local.track.utils import random_track, random_tracks
from tests.libraries.local.utils import path_playlist_resources
from tests.libraries.local.utils import path_playlist_xautopf_ra, path_playlist_xautopf_bp, path_playlist_xautopf_cm
from tests.libraries.local.utils import path_track_all, path_track_mp3, path_track_flac, path_track_wma
from tests.utils import path_txt, path_resources


class TestXAutoPF(LocalPlaylistTester):

    @pytest.fixture
    def playlist(self) -> XAutoPF:
        # needed to ensure __setitem__ check passes
        tracks = random_tracks(randrange(5, 15))
        tracks.append(random_track(cls=tracks[0].__class__))
        playlist = XAutoPF(path=path_playlist_xautopf_ra, tracks=tracks)
        return playlist

    def test_init_fails(self):
        tracks = random_tracks(20)

        # raises error on non-existent file, remove this once supported
        with pytest.raises(NotImplementedError):
            XAutoPF(path=join(dirname(path_playlist_xautopf_bp), "does_not_exist.xautopf"), tracks=tracks)

        with pytest.raises(InvalidFileType):
            XAutoPF(path=path_txt, tracks=tracks)

    def test_load_playlist_bp_settings(self, tracks: list[LocalTrack], path_mapper: PathMapper):
        pl = XAutoPF(path=path_playlist_xautopf_bp, path_mapper=path_mapper)

        assert pl.name == splitext(basename(path_playlist_xautopf_bp))[0]
        assert pl.description == "I am a description"
        assert pl.path == path_playlist_xautopf_bp
        assert pl.ext == splitext(basename(path_playlist_xautopf_bp))[1]
        assert not pl.tracks

        # fine-grained processor settings are tested in class-specific tests
        assert pl.matcher.ready
        assert len(pl.matcher.comparers.comparers) == 3
        assert not pl.limiter
        assert pl.sorter

        pl.load(tracks)
        assert [basename(track.path) for track in pl.tracks] == [basename(path_track_flac), basename(path_track_wma)]

    def test_load_playlist_bp_tracks(self, tracks: list[LocalTrack], path_mapper: PathMapper):
        # prepare tracks to search through
        tracks_actual = tracks
        tracks = random_tracks(50)
        for i, track in enumerate(tracks[10:40]):
            track.album = "an album"
        for i, track in enumerate(tracks[20:50]):
            track.artist = None
        for i, track in enumerate(tracks, 1):
            track.track_number = i
        tracks += tracks_actual

        pl = XAutoPF(path=path_playlist_xautopf_bp, tracks=tracks_actual, path_mapper=path_mapper)
        assert pl.tracks == tracks_actual[:2]

        pl = XAutoPF(path=path_playlist_xautopf_bp, tracks=tracks, path_mapper=path_mapper)
        assert len(pl.tracks) == 32
        tracks_expected = tracks_actual[:2] + [
            track for track in tracks if 20 < track.track_number < 30 or track.album == "an album"
        ]
        assert pl.tracks == sorted(tracks_expected, key=lambda t: t.track_number)

    def test_load_playlist_ra_settings(self, path_mapper: PathMapper):
        pl = XAutoPF(path=path_playlist_xautopf_ra, tracks=random_tracks(20), path_mapper=path_mapper)

        assert pl.name == splitext(basename(path_playlist_xautopf_ra))[0]
        assert pl.description is None
        assert pl.path == path_playlist_xautopf_ra
        assert pl.ext == splitext(basename(path_playlist_xautopf_ra))[1]

        # fine-grained processor settings are tested in class-specific tests
        assert not pl.matcher.ready
        assert not pl.matcher.comparers
        assert pl.limiter
        assert pl.sorter

    def test_load_playlist_ra_tracks(self, path_mapper: PathMapper):
        # prepare tracks to search through
        tracks = random_tracks(50)
        for i, track in enumerate(tracks):
            track.date_added = datetime.now().replace(minute=i)

        pl = XAutoPF(path=path_playlist_xautopf_ra, tracks=tracks, path_mapper=path_mapper)

        limit = pl.limiter.limit_max
        assert len(pl.tracks) == limit
        tracks_expected = sorted(tracks, key=lambda t: t.date_added, reverse=True)[:limit]
        assert pl.tracks == sorted(tracks_expected, key=lambda t: t.date_added, reverse=True)

    @pytest.mark.parametrize("path", [path_playlist_xautopf_bp], indirect=["path"])
    def test_save_playlist(self, tracks: list[LocalTrack], path: str, path_mapper: PathMapper, tmp_path: Path):
        # prepare tracks to search through
        tracks_actual = [track for track in tracks if track.path in [path_track_flac, path_track_wma]]
        tracks = random_tracks(50)
        for i, track in enumerate(tracks[10:40]):
            track.album = "an album"
        for i, track in enumerate(tracks[20:50]):
            track.artist = None
        for i, track in enumerate(tracks, 1):
            track.track_number = i
        tracks += tracks_actual

        pl = XAutoPF(path=path, tracks=tracks, path_mapper=path_mapper)

        assert pl.path == path
        assert len(pl.tracks) == 32
        original_dt_modified = pl.date_modified
        original_dt_created = pl.date_created
        original_xml = deepcopy(pl.xml)

        # perform some operations on the playlist
        pl.description = "new description"
        tracks_added = random_tracks(3)
        pl.tracks += tracks_added
        pl.tracks.pop(5)
        pl.tracks.pop(6)
        pl.tracks.remove(tracks_actual[0])

        # first test results on a dry run
        result = pl.save(dry_run=True)

        assert result.start == 32
        assert result.start_description == "I am a description"
        assert result.start_included == 3
        assert result.start_excluded == 3
        assert result.start_compared == 3
        assert not result.start_limiter
        assert result.start_sorter
        assert result.final == len(pl.tracks)
        assert result.final_description == pl.description
        assert result.final_included == 4
        assert result.final_excluded == 2
        assert result.final_compared == 3
        assert not result.start_limiter
        assert result.start_sorter

        assert pl.date_modified == original_dt_modified
        assert pl.date_created == original_dt_created
        assert pl.xml == original_xml

        pl.save(dry_run=False)

        if not os.getenv("GITHUB_ACTIONS"):
            # TODO: these assertions always fail on GitHub actions but not locally, why?
            assert pl.date_modified > original_dt_modified
            assert pl.date_created == original_dt_created

        assert pl.xml != original_xml
        assert pl.xml["SmartPlaylist"]["@GroupBy"] == original_xml["SmartPlaylist"]["@GroupBy"]
        assert pl.xml["SmartPlaylist"]["Source"]["Conditions"] == original_xml["SmartPlaylist"]["Source"]["Conditions"]

        # assert file has reported path count and paths in the file have been mapped to relative paths
        paths = pl.xml["SmartPlaylist"]["Source"]["ExceptionsInclude"].split("|")
        assert len(paths) == result.final_included
        for path in paths:
            assert path.startswith("../")


class TestXMLPlaylistParser(PrettyPrinterTester):

    @pytest.fixture
    def obj(self) -> XMLPlaylistParser:
        return XMLPlaylistParser(path=path_playlist_xautopf_ra)

    @pytest.fixture(scope="class")
    def path_mapper(self) -> PathStemMapper:
        """Yields a :py:class:`PathMapper` that can map paths from the test playlist files"""
        yield PathStemMapper(stem_map={"../": path_resources}, available_paths=path_track_all)

    def test_get_comparer_bp(self):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_bp)
        conditions = parser.xml_source["Conditions"]
        comparers = [parser._get_comparer(xml=condition) for condition in to_collection(conditions["Condition"])]

        assert len(comparers) == 3

        assert comparers[0].field == Fields.ALBUM
        assert not comparers[0]._converted
        assert comparers[0].expected == ["an album"]
        assert comparers[0].condition == "contains"
        assert comparers[0]._processor_method == comparers[0]._contains

        assert comparers[1].field == Fields.ARTIST
        assert not comparers[1]._converted
        assert comparers[1].expected is None
        assert comparers[1].condition == "is_null"
        assert comparers[1]._processor_method == comparers[1]._is_null

        assert comparers[2].field == Fields.TRACK_NUMBER
        assert not comparers[2]._converted
        assert comparers[2].expected == ["30"]
        assert comparers[2].condition == "less_than"
        assert comparers[2]._processor_method == comparers[2]._is_before

    def test_get_comparer_ra(self):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_ra)
        conditions = parser.xml_source["Conditions"]
        comparers = [parser._get_comparer(xml=condition) for condition in to_collection(conditions["Condition"])]

        assert len(comparers) == 1
        comparer = comparers[0]

        assert comparer.field == LocalTrackField.ALBUM
        assert not comparer._converted
        assert comparer.expected == [""]
        assert comparer.condition == "contains"
        assert comparer._processor_method == comparer._contains

    def test_get_matcher_bp(self, path_mapper: PathStemMapper):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_bp, path_mapper=path_mapper)
        matcher = parser.get_matcher()

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

        assert matcher.group_by == Fields.ALBUM

    def test_get_matcher_ra(self, path_mapper: PathStemMapper):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_ra, path_mapper=path_mapper)
        matcher = parser.get_matcher()

        assert len(matcher.include) == 0
        assert len(matcher.exclude) == 0

        assert isinstance(matcher.comparers.comparers, dict)
        assert len(matcher.comparers.comparers) == 0
        assert not matcher.comparers.match_all
        assert all(not m[1].ready for m in matcher.comparers.comparers.values())

        assert matcher.group_by is None

    def test_get_matcher_cm(self, path_mapper: PathStemMapper):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_cm, path_mapper=path_mapper)
        matcher = parser.get_matcher()

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

        assert matcher.group_by == Fields.ALBUM

    def test_get_limiter_bp(self):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_bp)
        assert parser.get_limiter() is None

    def test_get_limiter_ra(self):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_ra)
        limiter = parser.get_limiter()

        assert limiter.limit_max == 20
        assert limiter.kind == LimitType.ITEMS
        assert limiter.allowance == 1.25
        assert limiter._processor_method == limiter._most_recently_added

    def test_get_sorter_bp(self):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_bp)

        # shuffle settings not set as automatic order defined
        sorter = parser.get_sorter()
        assert sorter.sort_fields == {Fields.TRACK_NUMBER: False}
        assert sorter.shuffle_mode is None
        assert sorter.shuffle_weight == 0.0

        # flip sorting to manual order to force function to set shuffle settings
        parser.xml_source["SortBy"]["@Field"] = "78"
        sorter = parser.get_sorter()
        assert sorter.sort_fields == {}
        assert sorter.shuffle_mode == ShuffleMode.RECENT_ADDED
        assert sorter.shuffle_weight == 0.5

    def test_get_sorter_ra(self):
        parser = XMLPlaylistParser(path=path_playlist_xautopf_ra)

        # shuffle settings not set as automatic order defined
        sorter = parser.get_sorter()
        assert sorter.sort_fields == {Fields.DATE_ADDED: True}
        assert sorter.shuffle_mode is None
        assert sorter.shuffle_weight == 0.0

        # flip sorting to manual order to force function to set shuffle settings
        parser.xml_source["SortBy"]["@Field"] = "78"
        sorter = parser.get_sorter()
        assert sorter.sort_fields == {}
        assert sorter.shuffle_mode == ShuffleMode.DIFFERENT_ARTIST
        assert sorter.shuffle_weight == -0.2


@pytest.mark.manual
@pytest.fixture(scope="module")
def library() -> LocalLibrary:
    """Yields a loaded :py:class:`LocalLibrary` to supply tracks for manual checking of custom playlist files"""
    mapper = PathStemMapper({"../..": os.getenv("TEST_PL_LIBRARY", "")})
    library = MusicBee(musicbee_folder=join(os.getenv("TEST_PL_LIBRARY"), "MusicBee"), path_mapper=mapper)
    library.load_tracks()
    return library


# noinspection PyTestUnpassedFixture, SpellCheckingInspection
@pytest.mark.manual
@pytest.mark.skipif(
    "not config.getoption('-m') and not config.getoption('-k')",
    reason="Only runs when the test or marker is specified explicitly by the user",
)
@pytest.mark.parametrize("source,expected", [
    (
        join(os.getenv("TEST_PL_SOURCE", ""), f"{splitext(basename(name))[0]}.xautopf"),
        join(os.getenv("TEST_PL_COMPARISON", ""), f"{splitext(basename(name))[0]}.m3u"),
    )
    for name in glob(join(os.getenv("TEST_PL_SOURCE", ""), "**", "*.xautopf"), recursive=True)
])
def test_playlist_paths_manual(library: LocalLibrary, source: str, expected: str):
    assert exists(source)
    assert exists(expected)

    pl = library.load_playlist(source)

    with open(expected, "r", encoding="utf-8") as f:
        paths_expected = [library.path_mapper.map(line.strip()) for line in f]

    assert sorted(track.path for track in pl) == sorted(paths_expected)
    assert [track.path for track in pl] == paths_expected
