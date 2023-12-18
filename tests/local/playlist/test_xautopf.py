import sys
from datetime import datetime
from os.path import dirname, join, splitext, basename
from random import randrange

import pytest

from syncify.fields import LocalTrackField
from syncify.local.exception import InvalidFileType
from syncify.local.playlist import XAutoPF
from syncify.local.track import LocalTrack
from syncify.processors.limit import LimitType
from syncify.processors.sort import ShuffleMode, ShuffleBy
from tests.local.playlist.utils import path_playlist_xautopf_ra, path_playlist_xautopf_bp
from tests.local.test_local_collection import LocalCollectionTester
from tests.local.utils import random_tracks, path_track_flac, path_track_wma, path_track_mp3, random_track
from tests.utils import path_txt, path_resources


# noinspection PyTestUnpassedFixture
class TestXAutoPF(LocalCollectionTester):

    @staticmethod
    @pytest.fixture
    def collection() -> XAutoPF:
        # needed to ensure __setitem__ check passes
        tracks = random_tracks(randrange(5, 15))
        tracks.append(random_track(cls=tracks[0].__class__))
        playlist = XAutoPF(path=path_playlist_xautopf_ra, tracks=tracks, check_existence=False)
        return playlist

    @staticmethod
    def test_init_fails():
        tracks = random_tracks(20)

        # raises error on non-existent file, remove this once supported
        with pytest.raises(NotImplementedError):
            XAutoPF(
                path=join(dirname(path_playlist_xautopf_bp), "does_not_exist.xautopf"), tracks=tracks,
            )

        with pytest.raises(InvalidFileType):
            XAutoPF(path=path_txt, tracks=tracks)

    @staticmethod
    def test_load_playlist_1_settings():
        pl = XAutoPF(
            path=path_playlist_xautopf_bp,
            tracks=random_tracks(20),  # just need to put something here, doesn't matter what for this test
            library_folder=path_resources,
            other_folders="../",
            check_existence=False,
        )

        assert pl.name == splitext(basename(path_playlist_xautopf_bp))[0]
        assert pl.description == "I am a description"
        assert pl.path == path_playlist_xautopf_bp
        assert pl.ext == splitext(basename(path_playlist_xautopf_bp))[1]

        # comparers
        assert pl.matcher.comparers[0].field == LocalTrackField.ALBUM
        assert pl.matcher.comparers[0].expected == ["an album"]
        assert not pl.matcher.comparers[0]._converted
        assert pl.matcher.comparers[0].condition == "contains"
        assert pl.matcher.comparers[0]._processor == pl.matcher.comparers[0]._contains
        assert pl.matcher.comparers[1].field == LocalTrackField.ARTIST
        assert pl.matcher.comparers[1].expected is None
        assert not pl.matcher.comparers[1]._converted
        assert pl.matcher.comparers[1].condition == "is_null"
        assert pl.matcher.comparers[1]._processor == pl.matcher.comparers[1]._is_null
        assert pl.matcher.comparers[2].field == LocalTrackField.TRACK_NUMBER
        assert pl.matcher.comparers[2].expected == [30]
        assert pl.matcher.comparers[2]._converted
        assert pl.matcher.comparers[2].condition == "less_than"
        assert pl.matcher.comparers[2]._processor == pl.matcher.comparers[2]._is_before

        # matcher
        assert pl.matcher.match_all
        assert pl.matcher.library_folder == path_resources.rstrip("\\/")
        assert pl.matcher.original_folder == ".."
        assert set(pl.matcher.include_paths) == {path_track_wma.casefold(), path_track_flac.casefold()}
        assert set(pl.matcher.exclude_paths) == {
            join(path_resources, basename(dirname(__file__)), "exclude_me_2.mp3").casefold(),
            path_track_mp3.casefold(),
            join(path_resources, basename(dirname(__file__)), "exclude_me.flac").casefold(),
        }

        # limit
        assert pl.limiter is None

        # sorter
        assert pl.sorter.sort_fields == {LocalTrackField.TRACK_NUMBER: False}
        assert pl.sorter.shuffle_mode == ShuffleMode.NONE  # switch to ShuffleMode.RECENT_ADDED once implemented
        assert pl.sorter.shuffle_by == ShuffleBy.ALBUM
        assert pl.sorter.shuffle_weight == 0.5

    @staticmethod
    def test_load_playlist_1_tracks(tracks: list[LocalTrack]):
        # prepare tracks to search through
        tracks_actual = tracks
        tracks = random_tracks(30)
        for i, track in enumerate(tracks[10:40]):
            track.album = "an album"
        for i, track in enumerate(tracks[20:50]):
            track.artist = None
        for i, track in enumerate(tracks, 1):
            track.track_number = i
        tracks += tracks_actual

        pl = XAutoPF(
            path=path_playlist_xautopf_bp,
            tracks=tracks_actual,
            library_folder=path_resources,
            other_folders="../",
            check_existence=True,
        )
        assert pl.tracks == tracks_actual[:2]

        pl = XAutoPF(
            path=path_playlist_xautopf_bp,
            tracks=tracks,
            library_folder=path_resources,
            other_folders="../",
            check_existence=False,
        )
        assert len(pl.tracks) == 11
        tracks_expected = tracks_actual[:2] + [track for track in tracks if 20 < track.track_number < 30]
        assert pl.tracks == sorted(tracks_expected, key=lambda t: t.track_number)

    @staticmethod
    def test_load_playlist_2_settings():
        pl = XAutoPF(
            path=path_playlist_xautopf_ra,
            tracks=random_tracks(20),  # just need to put something here, doesn't matter what for this test
            library_folder=path_resources,
            other_folders="../",
            check_existence=False,
        )

        assert pl.name == splitext(basename(path_playlist_xautopf_ra))[0]
        assert pl.description is None
        assert pl.path == path_playlist_xautopf_ra
        assert pl.ext == splitext(basename(path_playlist_xautopf_ra))[1]

        # matcher
        assert len(pl.matcher.comparers) == 0
        assert not pl.matcher.match_all
        assert pl.matcher.library_folder == path_resources.rstrip("\\/")
        assert pl.matcher.original_folder is None
        assert len(pl.matcher.include_paths) == 0
        assert len(pl.matcher.exclude_paths) == 0

        # limit
        assert pl.limiter.limit_max == 20
        assert pl.limiter.kind == LimitType.ITEMS
        assert pl.limiter.allowance == 1.25
        assert pl.limiter._processor == pl.limiter._most_recently_added

        # sorter
        assert pl.sorter.sort_fields == {LocalTrackField.DATE_ADDED: True}
        assert pl.sorter.shuffle_mode == ShuffleMode.NONE
        assert pl.sorter.shuffle_by == ShuffleBy.TRACK
        assert pl.sorter.shuffle_weight == 0

    @staticmethod
    def test_load_playlist_2_tracks():
        # prepare tracks to search through
        tracks = random_tracks(50)
        for i, track in enumerate(tracks):
            track.date_added = datetime.now().replace(minute=i)

        pl = XAutoPF(
            path=path_playlist_xautopf_ra,
            tracks=tracks,
            library_folder=path_resources,
            other_folders="../",
            check_existence=False,
        )
        limit = pl.limiter.limit_max
        assert len(pl.tracks) == limit
        tracks_expected = sorted(tracks, key=lambda t: t.date_added, reverse=True)[:limit]
        assert pl.tracks == sorted(tracks_expected, key=lambda t: t.date_added, reverse=True)

    @staticmethod
    @pytest.mark.parametrize("path", [path_playlist_xautopf_bp], indirect=["path"])
    def test_save_playlist(tracks: list[LocalTrack], path: str, tmp_path: str):
        # prepare tracks to search through
        tracks_actual = [track for track in tracks if track.path in [path_track_flac, path_track_wma]]
        tracks = random_tracks(30)
        for i, track in enumerate(tracks[10:40]):
            track.album = "an album"
        for i, track in enumerate(tracks[20:50]):
            track.artist = None
        for i, track in enumerate(tracks, 1):
            track.track_number = i
        tracks += tracks_actual

        pl = XAutoPF(
            path=path,
            tracks=tracks,
            library_folder=path_resources,
            other_folders="../",
            check_existence=False,
        )
        assert pl.path == path
        assert len(pl.tracks) == 11
        original_dt_modified = pl.date_modified
        original_dt_created = pl.date_created

        # perform some operations on the playlist
        pl.description = "new description"
        tracks_added = random_tracks(3)
        pl.tracks += tracks_added
        pl.tracks.pop(5)
        pl.tracks.pop(6)
        pl.tracks.remove(tracks_actual[0])

        # first test results on a dry run
        result = pl.save(dry_run=True)

        assert result.start == 11
        assert result.start_description == "I am a description"
        assert result.start_include == 3
        assert result.start_exclude == 3
        assert result.start_comparers == 3
        assert not result.start_limiter
        assert result.start_sorter
        assert result.final == len(pl.tracks)
        assert result.final_description == pl.description
        assert result.final_include == 4
        assert result.final_exclude == 2
        assert result.final_comparers == 3
        assert not result.start_limiter
        assert result.start_sorter

        assert pl.date_modified == original_dt_modified
        assert pl.date_created == original_dt_created

        # save the file and check it has been modified
        pl.save(dry_run=False)
        assert pl.date_modified > original_dt_modified
        if sys.platform != "linux":
            # linux appears to always update the date created when modifying a file, skip this test on linux
            assert pl.date_created == original_dt_created
