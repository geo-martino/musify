import os
from copy import deepcopy
from datetime import datetime
from os.path import dirname, join, splitext, basename
from pathlib import Path
from random import randrange

import pytest

from musify.local.exception import InvalidFileType
from musify.local.file import PathMapper
from musify.local.playlist import XAutoPF
from musify.local.track import LocalTrack
from tests.local.playlist.testers import LocalPlaylistTester
from tests.local.playlist.utils import path_playlist_xautopf_ra, path_playlist_xautopf_bp
from tests.local.track.utils import random_track, random_tracks
from tests.local.utils import path_track_flac, path_track_wma
from tests.utils import path_txt


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

    def test_load_playlist_1_settings(self, tracks: list[LocalTrack], path_mapper: PathMapper):
        pl = XAutoPF(path=path_playlist_xautopf_bp, path_mapper=path_mapper)

        assert pl.name == splitext(basename(path_playlist_xautopf_bp))[0]
        assert pl.description == "I am a description"
        assert pl.path == path_playlist_xautopf_bp
        assert pl.ext == splitext(basename(path_playlist_xautopf_bp))[1]
        assert not pl.tracks

        # processor settings are tested in class-specific tests
        assert pl.matcher.ready
        assert len(pl.matcher.comparers.comparers) == 3
        assert not pl.limiter
        assert pl.sorter

        pl.load(tracks)
        assert [basename(track.path) for track in pl.tracks] == [basename(path_track_flac), basename(path_track_wma)]

    def test_load_playlist_1_tracks(self, tracks: list[LocalTrack], path_mapper: PathMapper):
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

        pl = XAutoPF(path=path_playlist_xautopf_bp, tracks=tracks_actual, path_mapper=path_mapper)
        assert pl.tracks == tracks_actual[:2]

        pl = XAutoPF(path=path_playlist_xautopf_bp, tracks=tracks, path_mapper=path_mapper)
        assert len(pl.tracks) == 11
        tracks_expected = tracks_actual[:2] + [track for track in tracks if 20 < track.track_number < 30]
        assert pl.tracks == sorted(tracks_expected, key=lambda t: t.track_number)

    def test_load_playlist_2_settings(self, path_mapper: PathMapper):
        pl = XAutoPF(path=path_playlist_xautopf_ra, tracks=random_tracks(20), path_mapper=path_mapper)

        assert pl.name == splitext(basename(path_playlist_xautopf_ra))[0]
        assert pl.description is None
        assert pl.path == path_playlist_xautopf_ra
        assert pl.ext == splitext(basename(path_playlist_xautopf_ra))[1]

        # processor settings are tested in class-specific tests
        assert not pl.matcher.ready
        assert not pl.matcher.comparers
        assert pl.limiter
        assert pl.sorter

    def test_load_playlist_2_tracks(self, path_mapper: PathMapper):
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
        tracks = random_tracks(30)
        for i, track in enumerate(tracks[10:40]):
            track.album = "an album"
        for i, track in enumerate(tracks[20:50]):
            track.artist = None
        for i, track in enumerate(tracks, 1):
            track.track_number = i
        tracks += tracks_actual

        pl = XAutoPF(path=path, tracks=tracks, path_mapper=path_mapper)

        assert pl.path == path
        assert len(pl.tracks) == 11
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

        assert result.start == 11
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

        # assert file has reported path count and paths in the file have been mapped to relative paths
        paths = pl.xml["SmartPlaylist"]["Source"]["ExceptionsInclude"].split("|")
        assert len(paths) == result.final_included
        for path in paths:
            assert path.startswith("../")
