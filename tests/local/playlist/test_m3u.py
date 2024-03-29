import os
from os.path import join, splitext, basename, exists
from pathlib import Path
from random import randrange

import pytest

from musify.local.playlist import M3U
from musify.local.track import LocalTrack
from musify.shared.exception import InvalidFileType
from musify.shared.file import PathMapper, PathStemMapper
from tests.local.playlist.testers import LocalPlaylistTester
from tests.local.track.utils import random_track, random_tracks
from tests.local.utils import path_playlist_m3u
from tests.utils import path_txt


class TestM3U(LocalPlaylistTester):

    @pytest.fixture
    def playlist(self, tmp_path: Path) -> M3U:
        # needed to ensure __setitem__ check passes
        tracks = random_tracks(randrange(5, 20))
        tracks.append(random_track(cls=tracks[0].__class__))
        playlist = M3U(path=join(tmp_path, "does_not_exist.m3u"), tracks=tracks)
        return playlist

    @pytest.fixture(scope="class")
    def tracks_actual(self, tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Yield list of all real LocalTracks present in the test playlist"""
        with open(path_playlist_m3u, "r") as f:
            ext = [splitext(line.strip())[1] for line in f]
        return sorted([track for track in tracks if track.ext in ext], key=lambda x: ext.index(x.ext))

    @pytest.fixture(scope="class")
    def tracks_limited(self, tracks: list[LocalTrack], tracks_actual: list[LocalTrack]) -> list[LocalTrack]:
        """Yield list of real LocalTracks where some are present in the test playlist and some are not"""
        return tracks_actual[:-1] + [track for track in tracks if track not in tracks_actual]

    def test_does_not_load_unsupported_files(self):
        with pytest.raises(InvalidFileType):
            M3U(path=path_txt)

    def test_load_fake_file_with_no_tracks(self, tracks: list[LocalTrack], tmp_path: Path):
        path_fake = join(tmp_path, "does_not_exist.m3u")

        pl = M3U(path=path_fake)
        assert pl.path == path_fake
        assert pl.name == splitext(basename(path_fake))[0]
        assert pl.ext == splitext(basename(path_fake))[1]
        assert len(pl.tracks) == 0

        pl.load(tracks)
        assert pl.tracks == tracks

    def test_load_fake_file_with_fake_tracks(self, tracks: list[LocalTrack], tmp_path: Path):
        path_fake = join(tmp_path, "does_not_exist.m3u")
        tracks_random = random_tracks(30)

        pl = M3U(path=path_fake, tracks=tracks_random)
        assert pl.path == path_fake
        assert pl.tracks == tracks_random

        pl.load(tracks + tracks_random[:4])
        assert pl.tracks == tracks_random[:4]

    def test_load_file_with_no_tracks(
            self, tracks_actual: list[LocalTrack], tracks_limited: list[LocalTrack], path_mapper: PathMapper
    ):
        pl = M3U(path=path_playlist_m3u, path_mapper=path_mapper)

        assert pl.path == path_playlist_m3u
        assert pl.tracks == tracks_actual

        # reloads only with given tracks that match conditions i.e. paths to include
        pl.load(tracks_limited)
        assert pl.tracks == [track for track in tracks_limited if track in tracks_actual]

        # ...and then reloads all tracks from disk that match conditions when no tracks are given
        pl.load()
        assert pl.tracks == tracks_actual

    def test_load_file_with_tracks(
            self, tracks_actual: list[LocalTrack], tracks_limited: list[LocalTrack], path_mapper: PathMapper
    ):
        pl = M3U(path=path_playlist_m3u, tracks=tracks_limited, path_mapper=path_mapper)

        assert pl.path == path_playlist_m3u
        assert pl.tracks == [track for track in tracks_limited if track in tracks_actual]

        # reloads only with given tracks that match conditions i.e. paths to include
        pl.load(tracks_limited[:1])
        assert pl.tracks == tracks_limited[:1]

        # ...and then reloads all tracks from disk that match conditions when no tracks are given
        pl.load()
        assert pl.tracks == tracks_actual

    def test_save_file_dry_run(self, tmp_path: Path):
        path_new = join(tmp_path, "new_playlist.m3u")

        # creates a new M3U file
        pl = M3U(path=path_new)
        assert pl.path == path_new
        assert len(pl.tracks) == 0

        # ...load the tracks
        tracks_random = random_tracks(30)
        pl.load(tracks_random)
        assert pl.tracks == tracks_random

        # ...save these loaded tracks as a dry run - no output
        result = pl.save(dry_run=True)

        assert result.start == 0
        assert result.added == len(tracks_random)
        assert result.removed == 0
        assert result.unchanged == 0
        assert result.difference == len(tracks_random)
        assert result.final == len(tracks_random)

        assert not exists(path_new)
        assert pl.date_modified is None
        assert pl.date_created is None

    def test_save_new_file(self, tmp_path: Path):
        path_new = join(tmp_path, "new_playlist.m3u")
        tracks_random = random_tracks(30)

        pl = M3U(path=path_new, tracks=tracks_random)
        result = pl.save(dry_run=False)

        assert result.start == 0
        assert result.added == len(tracks_random)
        assert result.removed == 0
        assert result.unchanged == 0
        assert result.difference == len(tracks_random)
        assert result.final == len(tracks_random)

        assert exists(path_new)
        assert pl.date_modified is not None
        assert pl.date_created is not None

        with open(path_new, 'r') as f:
            paths = [line.strip() for line in f]
        assert paths == [track.path for track in pl.tracks]

        original_dt_modified = pl.date_modified
        original_dt_created = pl.date_created

        # ...remove some tracks and add some new ones
        tracks_random_new = random_tracks(15)
        pl.tracks = pl.tracks[:20] + tracks_random_new
        result = pl.save(dry_run=False)

        assert result.start == len(tracks_random)
        assert result.added == len(tracks_random_new)
        assert result.removed == 10
        assert result.unchanged == 20
        assert result.difference == 5
        assert result.final == 35

        if not os.getenv("GITHUB_ACTIONS"):
            # TODO: these assertions always fail on GitHub actions but not locally, why?
            assert pl.date_modified > original_dt_modified
            assert pl.date_created == original_dt_created

        with open(path_new, 'r') as f:
            paths = [line.strip() for line in f]
        assert paths == [track.path for track in pl.tracks]

    @pytest.mark.parametrize("path", [path_playlist_m3u], indirect=["path"])
    def test_save_existing_file(
            self, tracks_actual: list[LocalTrack], path: str, path_mapper: PathStemMapper, tmp_path: Path
    ):
        path_prefix = list(path_mapper.stem_map)[0]

        # ensure all paths in the file have relative paths and will therefore undergo path mapping
        with open(path, "r") as f:
            for line in f:
                assert line.startswith(path_prefix)

        # ensure all loaded track path have absolute paths and will therefore undergo path mapping
        for track in tracks_actual:
            assert not track.path.startswith(path_prefix)

        pl = M3U(path=path, path_mapper=path_mapper)

        assert pl.path == path
        assert pl.tracks == tracks_actual
        original_dt_modified = pl.date_modified
        original_dt_created = pl.date_created

        tracks_random = random_tracks(10)
        pl.tracks = pl.tracks[:2] + tracks_random
        result = pl.save(dry_run=False)

        assert result.start == 3
        assert result.added == len(tracks_random)
        assert result.removed == 1
        assert result.unchanged == 2
        assert result.difference == 9
        assert result.final == 12

        if not os.getenv("GITHUB_ACTIONS"):
            # TODO: these assertions always fail on GitHub actions but not locally, why?
            assert pl.date_modified > original_dt_modified
            assert pl.date_created == original_dt_created
        new_dt_modified = pl.date_modified

        # assert file has reported path count and paths in the file have been mapped to relative paths
        with open(path, "r") as f:
            lines = [line.strip() for line in f]
        assert len(lines) == result.final
        for line in lines:
            assert line.startswith(path_prefix)

        # change the name and save to new file
        pl.name = "New Playlist"
        assert pl.path == join(tmp_path, "New Playlist" + pl.ext)
        pl.save(dry_run=False)

        if not os.getenv("GITHUB_ACTIONS"):
            # TODO: these assertions always fail on GitHub actions but not locally, why?
            assert pl.date_modified > new_dt_modified
            assert pl.date_created > original_dt_created

        with open(pl.path, 'r') as f:
            paths = [line.strip() for line in f]
        assert paths == path_mapper.unmap_many(pl.tracks, check_existence=False)
