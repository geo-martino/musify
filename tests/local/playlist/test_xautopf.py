import sys
from datetime import datetime
from os.path import dirname, join, splitext, basename
from random import randrange

import pytest

from syncify.fields import LocalTrackField
from syncify.local.exception import InvalidFileType
from syncify.local.playlist import XAutoPF
from syncify.local.track import LocalTrack
from tests.local.playlist.utils import LocalPlaylistTester, path_playlist_xautopf_ra, path_playlist_xautopf_bp
from tests.local.utils import random_tracks, path_track_flac, path_track_wma, random_track
from tests.utils import path_txt, path_resources


# noinspection PyTestUnpassedFixture
class TestXAutoPF(LocalPlaylistTester):

    @pytest.fixture
    def playlist(self) -> XAutoPF:
        # needed to ensure __setitem__ check passes
        tracks = random_tracks(randrange(5, 15))
        tracks.append(random_track(cls=tracks[0].__class__))
        for track in tracks:
            print(track)
        playlist = XAutoPF(path=path_playlist_xautopf_ra, tracks=tracks, check_existence=False)
        return playlist

    def test_init_fails(self):
        tracks = random_tracks(20)

        # raises error on non-existent file, remove this once supported
        with pytest.raises(NotImplementedError):
            XAutoPF(
                path=join(dirname(path_playlist_xautopf_bp), "does_not_exist.xautopf"), tracks=tracks,
            )

        with pytest.raises(InvalidFileType):
            XAutoPF(path=path_txt, tracks=tracks)

    def test_load_playlist_1_settings(self):
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

        # processor settings are tested in class-specific tests
        assert pl.matcher
        assert len(pl.matcher.comparers) == 3
        assert not pl.limiter
        assert pl.sorter

        # check the comparers have now converted expected values after load
        assert pl.matcher.comparers[2].field == LocalTrackField.TRACK_NUMBER
        assert pl.matcher.comparers[2]._converted
        assert pl.matcher.comparers[2].expected == [30]

    def test_load_playlist_1_tracks(self, tracks: list[LocalTrack]):
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

    def test_load_playlist_2_settings(self):
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

        # processor settings are tested in class-specific tests
        assert pl.matcher
        assert not pl.matcher.comparers
        assert pl.limiter
        assert pl.sorter

    def test_load_playlist_2_tracks(self):
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

    @pytest.mark.parametrize("path", [path_playlist_xautopf_bp], indirect=["path"])
    def test_save_playlist(self, tracks: list[LocalTrack], path: str, tmp_path: str):
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
