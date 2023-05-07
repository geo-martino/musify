from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname

import pytest

from syncify.local.files import FLAC, IllegalFileTypeError
from tests.common import path_txt
from tests.local.files.track.track import path_track_flac, path_track_resources
from tests.local.files.track.track import update_tags_test, clear_tags_test, update_images_test


def test_load():
    track = FLAC(file=path_track_flac)

    track_file = track.file

    track.load_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    # has actually reloaded the file in each reload
    assert id(track_file) != id(track_reload_1) != id(track_reload_2)

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        FLAC(path_txt)

    # raises error on files that do not exist
    with pytest.raises(FileNotFoundError):
        FLAC("does_not_exist.flac")


def test_copy():
    track = FLAC(file=path_track_flac)

    track_from_file = FLAC(file=track.file)
    assert id(track.file) == id(track_from_file.file)

    track_copy = copy(track)
    assert id(track.file) == id(track_copy.file)
    for key, value in vars(track).items():
        assert value == getattr(track_copy, key)

    track_deepcopy = deepcopy(track)
    assert id(track.file) != id(track_deepcopy.file)
    for key, value in vars(track).items():
        assert value == getattr(track_deepcopy, key)


def test_set_and_find_file_paths():
    track = FLAC(file=path_track_flac.upper())
    assert track.path == path_track_flac.upper()

    paths = FLAC.get_filepaths(path_track_resources)
    assert paths == {path_track_flac}

    track = FLAC(file=path_track_flac.upper(), available=paths)
    assert track.path != path_track_flac.upper()


def test_loaded_attributes():
    track = FLAC(file=path_track_flac)

    # metadata
    assert track.title == 'title 1'
    assert track.artist == 'artist 1'
    assert track.album == 'album artist 1'
    assert track.album_artist == 'various'
    assert track.track_number == 1
    assert track.track_total == 4
    assert track.genres == ['Pop', 'Rock', 'Jazz']
    assert track.year == 2020
    assert track.bpm == 120.12
    assert track.key == 'A'
    assert track.disc_number == 1
    assert track.disc_total == 3
    assert track.compilation
    assert track.comments == ['spotify:track:6fWoFduMpBem73DMLCOh1Z']

    assert track.uri == track.comments[0]
    assert track.has_uri

    assert track.image_links is None
    assert track.has_image

    # file properties
    assert track.path == path_track_flac
    assert track.folder == basename(dirname(path_track_flac))
    assert track.filename == basename(path_track_flac)
    assert track.ext == '.flac'
    assert track.size == 1818191
    assert int(track.length) == 20
    assert track.date_modified == datetime(2023, 5, 1, 10, 24, 14, 903000)

    # library properties
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None
    assert track.rating is None


def test_cleared_tags():
    track = FLAC(file=path_track_flac)
    clear_tags_test(track)


def test_updated_tags():
    track = FLAC(file=path_track_flac)
    update_tags_test(track)


def test_updated_images():
    track = FLAC(file=path_track_flac)
    update_images_test(track)
