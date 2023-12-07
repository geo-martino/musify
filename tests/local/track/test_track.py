from datetime import datetime
from os.path import basename, dirname, splitext, getmtime

import pytest

from syncify.local.exception import InvalidFileType
from syncify.local.track import FLAC, M4A, MP3, WMA, load_track
from tests import path_txt, path_resources
from tests.local import remote_wrangler
from tests.local.track import class_path_map, all_local_track_tests, path_track_all


def test_load_track():
    for cls, path in class_path_map.items():
        track = load_track(path)
        assert track.__class__ == cls
        assert track.path == path

    # raises error on unrecognised file type
    with pytest.raises(InvalidFileType):
        load_track(path_txt)


def test_flac():
    all_local_track_tests(FLAC)
    assert len(FLAC.get_filepaths(path_resources)) == 2

    path = class_path_map[FLAC]
    track = FLAC(file=path, available=path_track_all, remote_wrangler=remote_wrangler)
    assert track.tag_sep == "; "

    # metadata
    assert track.title == "title 1"
    assert track.artist == "artist 1"
    assert track.artists == ["artist 1"]
    assert track.album == "album artist 1"
    assert track.album_artist == "various"
    assert track.track_number == 1
    assert track.track_total == 4
    assert track.genres == ["Pop", "Rock", "Jazz"]
    assert track.year == 2020
    assert track.bpm == 120.12
    assert track.key == 'A'
    assert track.disc_number == 1
    assert track.disc_total == 3
    assert track.compilation
    # noinspection SpellCheckingInspection
    assert track.comments == ["spotify:track:6fWoFduMpBem73DMLCOh1Z"]

    assert track.uri == track.comments[0]
    assert track.has_uri

    assert track.image_links == {}
    assert track.has_image

    # file properties
    assert int(track.length) == 20
    assert track.path == path
    assert track.folder == basename(dirname(path))
    assert track.filename == splitext(basename(path))[0]
    assert track.ext == ".flac"
    assert track.size == 1818191
    assert track.kind == track.__class__.__name__
    assert track.channels == 1
    assert track.bit_rate == 706.413
    assert track.bit_depth == 0.016
    assert track.sample_rate == 44.1

    # dates + library properties
    assert track.rating is None
    assert track.date_modified == datetime.fromtimestamp(getmtime(path))
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None


def test_mp3():
    all_local_track_tests(MP3)
    assert len(MP3.get_filepaths(path_resources)) == 2

    path = class_path_map[MP3]
    track = MP3(file=path, remote_wrangler=remote_wrangler)
    assert track.tag_sep == "; "

    # metadata
    assert track.title == "title 2"
    assert track.artist == "artist 2; another artist"
    assert track.artists == ["artist 2", "another artist"]
    assert track.album == "album artist 2"
    assert track.album_artist == "various"
    assert track.track_number == 3
    assert track.track_total == 4
    assert track.genres == ["Pop Rock", "Musical"]
    assert track.year == 2024
    assert track.bpm == 200.56
    assert track.key == 'C'
    assert track.disc_number == 2
    assert track.disc_total == 3
    assert not track.compilation
    # noinspection SpellCheckingInspection
    assert track.comments == ["spotify:track:1TjVbzJUAuOvas1bL00TiH"]

    assert track.uri == track.comments[0]
    assert track.has_uri

    assert track.image_links == {}
    assert track.has_image

    # file properties
    assert int(track.length) == 30
    assert track.path == path
    assert track.folder == basename(dirname(path))
    assert track.filename == splitext(basename(path))[0]
    assert track.ext == ".mp3"
    assert track.size == 411038
    assert track.kind == track.__class__.__name__
    assert track.channels == 1
    assert track.bit_rate == 96.0
    assert track.bit_depth is None
    assert track.sample_rate == 44.1

    # dates + library properties
    assert track.rating is None
    assert track.date_modified == datetime.fromtimestamp(getmtime(path))
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None


def test_m4a():
    all_local_track_tests(M4A)
    assert len(M4A.get_filepaths(path_resources)) == 1

    path = class_path_map[M4A]
    track = M4A(file=path, remote_wrangler=remote_wrangler)
    assert track.tag_sep == "; "

    # metadata
    assert track.title == "title 3"
    assert track.artist == "artist 3"
    assert track.artists == ["artist 3"]
    assert track.album == "album artist 3"
    assert track.album_artist == "various"
    assert track.track_number == 2
    assert track.track_total == 4
    assert track.genres == ["Dance", "Techno"]
    assert track.year == 2021
    assert track.bpm == 120.0
    assert track.key == 'B'
    assert track.disc_number == 1
    assert track.disc_total == 2
    assert track.compilation
    assert track.comments == ["spotify:track:4npv0xZO9fVLBmDS2XP9Bw"]

    assert track.uri == track.comments[0]
    assert track.has_uri

    assert track.image_links == {}
    assert track.has_image

    # file properties
    assert int(track.length) == 20
    assert track.path == path
    assert track.folder == basename(dirname(path))
    assert track.filename == splitext(basename(path))[0]
    assert track.ext == ".m4a"
    assert track.size == 302199
    assert track.kind == track.__class__.__name__
    assert track.channels == 2
    assert track.bit_rate == 98.17
    assert track.bit_depth == 0.016
    assert track.sample_rate == 44.1

    # dates + library properties
    assert track.rating is None
    assert track.date_modified == datetime.fromtimestamp(getmtime(path))
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None


def test_wma():
    all_local_track_tests(WMA)
    assert len(WMA.get_filepaths(path_resources)) == 1

    path = class_path_map[WMA]
    track = WMA(file=path, remote_wrangler=remote_wrangler)
    assert track.tag_sep == "; "

    # metadata
    assert track.title == "title 4"
    assert track.artist == "artist 4"
    assert track.artists == ["artist 4"]
    assert track.album == "album artist 4"
    assert track.album_artist == "various"
    assert track.track_number == 4
    assert track.track_total == 4
    assert track.genres == ["Metal", "Rock"]
    assert track.year == 2023
    assert track.bpm == 200.56
    assert track.key == 'D'
    assert track.disc_number == 3
    assert track.disc_total == 4
    assert not track.compilation
    assert track.comments == [remote_wrangler.unavailable_uri_dummy]

    assert track.uri is None
    assert not track.has_uri

    assert track.image_links == {}
    assert track.has_image

    # file properties
    assert int(track.length) == 32
    assert track.path == path
    assert track.folder == basename(dirname(path))
    assert track.filename == splitext(basename(path))[0]
    assert track.ext == ".wma"
    assert track.size == 1193637
    assert track.kind == track.__class__.__name__
    assert track.channels == 1
    assert track.bit_rate == 96.0
    assert track.bit_depth is None
    assert track.sample_rate == 44.1

    # dates + library properties
    assert track.rating is None
    assert track.date_modified == datetime.fromtimestamp(getmtime(path))
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None
