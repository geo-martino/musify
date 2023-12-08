import os
import sys
from os.path import dirname, join, splitext, basename, exists

import pytest

from syncify.local.exception import InvalidFileType
from syncify.local.playlist import M3U
from syncify.local.track import LocalTrack, FLAC, M4A, MP3, WMA
from tests import path_txt
from tests.abstract.misc import pretty_printer_tests
from tests.local.playlist import copy_playlist_file, path_playlist_m3u, path_resources, path_playlist_cache
from tests.local.track import path_track_flac, path_track_m4a, path_track_wma, path_track_mp3, path_track_all
from tests.local.track import random_tracks

path_fake = join(dirname(path_playlist_m3u), "does_not_exist.m3u")


def get_tracks() -> list[LocalTrack]:
    """Load list of real LocalTracks"""
    return [FLAC(file=path_track_flac), WMA(file=path_track_wma), M4A(file=path_track_m4a)]


def test_load_fake_file_with_no_tracks():
    # initialising on a non-existent file and no tracks
    pl = M3U(path=path_fake)
    assert pl.path == path_fake
    assert pl.name == splitext(basename(path_fake))[0]
    assert pl.ext == splitext(basename(path_fake))[1]
    assert len(pl.tracks) == 0

    # ...and then loads all given tracks
    tracks = get_tracks()
    pl.load(tracks)
    assert pl.tracks == tracks

    pretty_printer_tests(pl)


def test_load_fake_file_with_bad_tracks():
    # initialising on a non-existent file and tracks
    tracks_random = random_tracks(30)
    pl = M3U(path=path_fake, tracks=tracks_random)
    assert pl.path == path_fake
    assert pl.tracks == tracks_random

    # ...and then loads all given tracks
    tracks = get_tracks()
    pl.load(tracks)
    assert pl.tracks == tracks

    pretty_printer_tests(pl)


def test_load_file_with_no_tracks():
    # initialising on a real file and no tracks
    pl = M3U(
        path=path_playlist_m3u,
        library_folder=path_resources,
        other_folders="../",
        available_track_paths=path_track_all,
    )
    assert pl.path == path_playlist_m3u
    assert len(pl.tracks) == 3
    assert sorted(track.ext for track in pl.tracks) == sorted([".wma", ".mp3", ".flac"])
    tracks_original = pl.tracks.copy()

    # ...and then reloads only with given tracks that match conditions i.e. paths to include
    tracks = get_tracks()
    pl.load(tracks)
    assert pl.tracks == tracks[:2]

    # ...and then reloads all tracks from disk that match conditions when no tracks are given
    pl.load()
    assert pl.tracks == tracks_original

    pretty_printer_tests(pl)


def test_load_file_with_tracks():
    tracks = get_tracks()

    # initialising on a real file and tracks given
    pl = M3U(
        path=path_playlist_m3u,
        tracks=tracks,
        library_folder=path_resources,
        other_folders="../",
        available_track_paths=path_track_all,
    )
    assert pl.path == path_playlist_m3u
    assert pl.tracks == tracks[:2]

    # ...and then reloads only with given tracks that match conditions i.e. paths to include
    pl.load(tracks)
    assert pl.tracks == tracks[:2]

    # ...and then reloads all tracks from disk that match conditions when no tracks are given
    pl.load()
    assert pl.tracks == [FLAC(path_track_flac), MP3(path_track_mp3), WMA(path_track_wma)]

    # raises error on unrecognised file type
    with pytest.raises(InvalidFileType):
        M3U(path=path_txt)

    pretty_printer_tests(pl)


def test_save_new_file():
    path_new = join(path_playlist_cache, "new_playlist.m3u")
    if exists(path_new):
        os.remove(path_new)

    # creates a new M3U file
    pl = M3U(path=path_new)
    assert pl.path == path_new
    assert len(pl.tracks) == 0

    # ...load the tracks
    tracks_random = random_tracks(30)
    pl.load(tracks_random)
    assert pl.tracks == tracks_random

    # ...save these loaded tracks first as a dry run - no output
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

    # ...save these loaded tracks for real
    pl = M3U(path=path_new)
    pl.load(tracks_random)
    result = pl.save(dry_run=False)

    assert result.start == 0
    assert result.added == len(tracks_random)
    assert result.removed == 0
    assert result.unchanged == 0
    assert result.difference == len(tracks_random)
    assert result.final == len(tracks_random)

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

    assert pl.date_modified > original_dt_modified
    if sys.platform != "linux":
        # linux appears to always update the date created when modifying a file, skip this test on linux
        assert pl.date_created == original_dt_created

    with open(path_new, 'r') as f:
        paths = [line.strip() for line in f]
    assert paths == [track.path for track in pl.tracks]

    os.remove(path_new)


def test_save_existing_file():
    # loading from an existing M3U file and giving it a new name
    _, path_file_copy = copy_playlist_file(path_playlist_m3u)
    pl = M3U(
        path=path_file_copy,
        library_folder=path_resources,
        other_folders="../",
        available_track_paths=path_track_all,
    )
    assert pl.path == path_file_copy
    assert len(pl.tracks) == 3
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

    assert pl.date_modified > original_dt_modified
    if sys.platform != "linux":
        # linux appears to always update the date created when modifying a file, skip this test on linux
        assert pl.date_created == original_dt_created
    new_dt_modified = pl.date_modified

    # change the name and save to new file
    pl.name = "New Playlist"
    pl.save(dry_run=False)

    assert pl.date_modified > new_dt_modified
    assert pl.date_created > original_dt_created

    with open(pl.path, 'r') as f:
        paths = [line.strip() for line in f]
    assert paths == pl._prepare_paths_for_output([track.path for track in pl.tracks])

    os.remove(path_file_copy)
    os.remove(pl.path)
