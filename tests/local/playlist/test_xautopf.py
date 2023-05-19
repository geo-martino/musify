import os
from datetime import datetime
from os.path import dirname, join, splitext, basename
from typing import List

import pytest

from syncify.enums.tags import TagName, PropertyName
from syncify.local.exception import IllegalFileTypeError
from syncify.local.playlist import XAutoPF
from syncify.local.playlist.processor import LimitType, ShuffleMode, ShuffleBy
from syncify.local.track import LocalTrack, FLAC, M4A, WMA, MP3
from tests.common import path_txt
from tests.local.playlist.playlist import copy_playlist_file, path_resources
from tests.local.playlist.playlist import path_playlist_xautopf_ra, path_playlist_xautopf_bp
from tests.local.track.track import random_tracks, path_track_flac, path_track_m4a, path_track_wma, path_track_mp3


def test_init_fails():
    tracks = random_tracks(20)

    # raises error on non-existent file, remove this once supported
    with pytest.raises(NotImplementedError):
        XAutoPF(path=join(dirname(path_playlist_xautopf_bp), "does_not_exist.xautopf"), tracks=tracks)

    with pytest.raises(IllegalFileTypeError):
        XAutoPF(path=path_txt, tracks=tracks)


def test_load_playlist_1():
    tracks = random_tracks(20)

    pl = XAutoPF(
        path=path_playlist_xautopf_bp,
        tracks=tracks,
        library_folder=path_resources,
        other_folders="../",
        check_existence=False
    )

    assert pl.path == path_playlist_xautopf_bp
    assert pl.name == splitext(basename(path_playlist_xautopf_bp))[0]
    assert pl.ext == splitext(basename(path_playlist_xautopf_bp))[1]
    assert pl.description == "I am a description"

    # comparators
    assert pl.matcher.comparators[0].field == TagName.ALBUM
    assert pl.matcher.comparators[0].expected == ["an album"]
    assert not pl.matcher.comparators[0]._converted
    assert pl.matcher.comparators[0].condition == "Contains"
    assert pl.matcher.comparators[0]._method == pl.matcher.comparators[0]._cond_contains
    assert pl.matcher.comparators[1].field == TagName.ARTIST
    assert pl.matcher.comparators[1].expected is None
    assert not pl.matcher.comparators[1]._converted
    assert pl.matcher.comparators[1].condition == "IsNull"
    assert pl.matcher.comparators[1]._method == pl.matcher.comparators[1]._cond_is_null
    assert pl.matcher.comparators[2].field == TagName.TRACK
    assert pl.matcher.comparators[2].expected == [30]
    assert pl.matcher.comparators[2]._converted
    assert pl.matcher.comparators[2].condition == "LessThan"
    assert pl.matcher.comparators[2]._method == pl.matcher.comparators[2]._cond_is_before

    # matcher
    assert pl.matcher.match_all
    assert pl.matcher.library_folder == path_resources.rstrip("\\/")
    assert pl.matcher.original_folder == ".."
    assert pl.matcher.include_paths == [path_track_flac.lower(), path_track_wma.lower()]
    assert pl.matcher.exclude_paths == [
        join(path_resources, "playlist", "exclude_me.flac").lower(),
        join(path_resources, "playlist", "exclude_me_2.mp3").lower(),
        path_track_mp3.lower()
    ]

    # limit
    assert pl.limiter is None

    # sorter
    assert pl.sorter.sort_fields == {TagName.TRACK: False}
    assert pl.sorter.shuffle_mode == ShuffleMode.NONE  # switch to ShuffleMode.RECENT_ADDED once implemented
    assert pl.sorter.shuffle_by == ShuffleBy.ALBUM
    assert pl.sorter.shuffle_weight == 0.5

    # prepare tracks to search through
    tracks = random_tracks(30)
    for i, track in enumerate(tracks[10:40]):
        track.album = "an album"
    for i, track in enumerate(tracks[20:50]):
        track.artist = None
    for i, track in enumerate(tracks, 1):
        track.track_number = i
    tracks_actual: List[LocalTrack] = [
        FLAC(path_track_flac), WMA(path_track_wma), MP3(path_track_mp3), M4A(path_track_m4a)
    ]
    tracks += tracks_actual

    pl = XAutoPF(
        path=path_playlist_xautopf_bp,
        tracks=tracks_actual,
        library_folder=path_resources,
        other_folders="../",
        check_existence=True
    )
    assert pl.tracks == tracks_actual[:2]

    pl = XAutoPF(
        path=path_playlist_xautopf_bp,
        tracks=tracks,
        library_folder=path_resources,
        other_folders="../",
        check_existence=False
    )
    assert len(pl.tracks) == 11
    tracks_expected = tracks_actual[:2] + [track for track in tracks if 20 < track.track_number < 30]
    assert pl.tracks == sorted(tracks_expected, key=lambda t: t.track_number)


def test_load_playlist_2():
    tracks = random_tracks(20)

    pl = XAutoPF(
        path=path_playlist_xautopf_ra,
        tracks=tracks,
        library_folder=path_resources,
        other_folders="../",
        check_existence=False
    )

    assert pl.path == path_playlist_xautopf_ra
    assert pl.name == splitext(basename(path_playlist_xautopf_ra))[0]
    assert pl.ext == splitext(basename(path_playlist_xautopf_ra))[1]
    assert pl.description is None

    # matcher
    assert pl.matcher.comparators is None
    assert not pl.matcher.match_all
    assert pl.matcher.library_folder == path_resources.rstrip("\\/")
    assert pl.matcher.original_folder is None
    assert pl.matcher.include_paths is None
    assert pl.matcher.exclude_paths is None

    # limit
    assert pl.limiter.limit_max == 20
    assert pl.limiter.kind == LimitType.ITEMS
    assert pl.limiter.allowance == 1.25
    assert pl.limiter._sort_method == pl.limiter._sort_most_recently_added

    # sorter
    assert pl.sorter.sort_fields == {PropertyName.DATE_ADDED: True}
    assert pl.sorter.shuffle_mode == ShuffleMode.NONE
    assert pl.sorter.shuffle_by == ShuffleBy.TRACK
    assert pl.sorter.shuffle_weight == 0

    # prepare tracks to search through
    tracks = random_tracks(50)
    for i, track in enumerate(tracks):
        track.date_added = datetime.now().replace(minute=i)

    pl = XAutoPF(
        path=path_playlist_xautopf_ra,
        tracks=tracks,
        library_folder=path_resources,
        other_folders="../",
        check_existence=False
    )
    limit = pl.limiter.limit_max
    assert len(pl.tracks) == limit
    tracks_expected = sorted(tracks, key=lambda t: t.date_added, reverse=True)[:limit]
    assert pl.tracks == sorted(tracks_expected, key=lambda t: t.date_added, reverse=True)


def test_save_playlist():
    _, path_file_copy = copy_playlist_file(path_playlist_xautopf_bp)

    # prepare tracks to search through
    tracks = random_tracks(30)
    for i, track in enumerate(tracks[10:40]):
        track.album = "an album"
    for i, track in enumerate(tracks[20:50]):
        track.artist = None
    for i, track in enumerate(tracks, 1):
        track.track_number = i
    tracks_actual: List[LocalTrack] = [FLAC(path_track_flac), WMA(path_track_wma)]
    tracks += tracks_actual

    pl = XAutoPF(
        path=path_file_copy,
        tracks=tracks,
        library_folder=path_resources,
        other_folders="../",
        check_existence=False
    )
    assert pl.path == path_file_copy
    assert len(pl.tracks) == 11

    # perform some operations on the playlist
    pl.description = "new description"
    tracks_added = random_tracks(3)
    pl.tracks += tracks_added
    pl.tracks.pop(5)
    pl.tracks.pop(6)
    pl.tracks.remove(tracks_actual[0])

    # first test results on a dry run
    original_dt = pl.date_modified
    result = pl.save()

    assert result.start == 11
    assert result.start_description == "I am a description"
    assert result.start_include == 3
    assert result.start_exclude == 3
    assert result.start_comparators == 3
    assert not result.start_limiter
    assert result.start_sorter
    assert result.final == len(pl.tracks)
    assert result.final_description == pl.description
    assert result.final_include == 4
    assert result.final_exclude == 2
    assert result.final_comparators == 3
    assert not result.start_limiter
    assert result.start_sorter

    assert pl.date_modified == original_dt

    # save the file and check it has been updated
    pl.save(dry_run=False)
    assert pl.date_modified > original_dt

    os.remove(path_file_copy)


