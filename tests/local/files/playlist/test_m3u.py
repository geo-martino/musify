import os
from os.path import dirname, join, splitext, basename
from typing import List

import pytest

from syncify.local.files import M3U, IllegalFileTypeError
from syncify.local.files.track import LocalTrack, FLAC, M4A, WMA
from tests.common import path_txt
from tests.local.files.playlist.playlist import copy_playlist_file, path_playlist_m3u, path_resources
from tests.local.files.track.track import random_tracks, path_track_flac, path_track_m4a, path_track_wma


def test_load():
    tracks: List[LocalTrack] = [FLAC(path_track_flac), WMA(path_track_wma), M4A(path_track_m4a)]

    # initialising on a non-existent file and no tracks
    path_fake = join(dirname(path_playlist_m3u), "does_not_exist.m3u")
    pl = M3U(path=path_fake)
    assert pl.path == path_fake
    assert pl.name == splitext(basename(path_fake))[0]
    assert pl.ext == splitext(basename(path_fake))[1]
    assert len(pl.tracks) == 0

    # ...and then loads all given tracks
    pl.load(tracks)
    assert pl.tracks == tracks

    # initialising on a non-existent file and tracks
    tracks_random = random_tracks(30)
    pl = M3U(path=path_fake, tracks=tracks_random)
    assert pl.path == path_fake
    assert pl.tracks == tracks_random

    # ...and then loads all given tracks
    pl.load(tracks)
    assert pl.tracks == tracks

    # initialising on a real file and no tracks
    pl = M3U(path=path_playlist_m3u, library_folder=path_resources, other_folders="../")
    assert pl.path == path_playlist_m3u
    assert len(pl.tracks) == 3
    assert sorted(track.ext for track in pl.tracks) == sorted([".wma", ".mp3", ".flac"])
    tracks_original = pl.tracks.copy()

    # ...and then reloads only with given tracks that match conditions i.e. paths to include
    pl.load(tracks)
    assert pl.tracks == tracks[:2]

    # ...and then reloads all tracks from disk that match conditions when no tracks are given
    pl.load()
    assert pl.tracks == tracks_original

    # initialising on a real file and tracks given
    pl = M3U(path=path_playlist_m3u, tracks=tracks, library_folder=path_resources, other_folders="../")
    assert pl.path == path_playlist_m3u
    assert pl.tracks == tracks[:2]

    # ...and then reloads only with given tracks that match conditions i.e. paths to include
    pl.load(tracks)
    assert pl.tracks == tracks[:2]

    # ...and then reloads all tracks from disk that match conditions when no tracks are given
    pl.load()
    assert pl.tracks == tracks_original

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        M3U(path=path_txt)


def test_save():
    path_new = join(dirname(path_playlist_m3u), "new_playlist.m3u")
    try:
        os.remove(path_new)
    except FileNotFoundError:
        pass

    # creates a new M3U file
    pl = M3U(path=path_new)
    assert pl.path == path_new
    assert len(pl.tracks) == 0

    # ...load the tracks
    tracks_random = random_tracks(30)
    pl.load(tracks_random)
    assert pl.tracks == tracks_random

    # ...save these loaded tracks
    result = pl.save()
    assert result.start == 0
    assert result.added == len(tracks_random)
    assert result.removed == 0
    assert result.unchanged == 0
    assert result.difference == len(tracks_random)
    assert result.final == len(tracks_random)

    with open(path_new, 'r') as f:
        paths = [line.strip() for line in f]
    assert paths == [track.path for track in pl.tracks]

    # ...remove some tracks and add some new ones
    tracks_random_new = random_tracks(15)
    pl.tracks = pl.tracks[:20] + tracks_random_new
    result = pl.save()
    assert result.start == len(tracks_random)
    assert result.added == len(tracks_random_new)
    assert result.removed == 10
    assert result.unchanged == 20
    assert result.difference == 5
    assert result.final == 35

    with open(path_new, 'r') as f:
        paths = [line.strip() for line in f]
    assert paths == [track.path for track in pl.tracks]

    os.remove(path_new)

    # loading from an existing M3U file and giving it a new name
    _, path_file_copy = copy_playlist_file(path_playlist_m3u)
    pl = M3U(path=path_file_copy, library_folder=path_resources, other_folders="../")
    assert pl.path == path_file_copy
    assert len(pl.tracks) == 3

    tracks_random = random_tracks(10)
    pl.tracks = pl.tracks[:2] + tracks_random
    pl.name = "New Playlist"
    result = pl.save()

    assert result.start == 3
    assert result.added == len(tracks_random)
    assert result.removed == 1
    assert result.unchanged == 2
    assert result.difference == 9
    assert result.final == 12

    with open(pl.path, 'r') as f:
        paths = [line.strip() for line in f]
    assert paths == pl._prepare_paths_for_output([track.path for track in pl.tracks])

    os.remove(path_file_copy)
    os.remove(pl.path)

