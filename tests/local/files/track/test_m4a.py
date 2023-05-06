from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname

import pytest

from syncify.local.files import M4A, IllegalFileTypeError
from tests.common import path_txt
from tests.local.files.track.track import path_track_m4a, path_track_resources, update_tags_test, clear_tags_test, update_images_test


def test_load():
    track = M4A(file=path_track_m4a)

    track_file = track.file

    track.load_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    # has actually reloaded the file in each reload
    assert id(track_file) != id(track_reload_1) != id(track_reload_2)

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        M4A(path_txt)

    # raises error on files that do not exist
    with pytest.raises(FileNotFoundError):
        M4A("does_not_exist.m4a")


def test_copy():
    track = M4A(file=path_track_m4a)

    track_from_file = M4A(file=track.file)
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
    track = M4A(file=path_track_m4a.upper())
    assert track.path == path_track_m4a.upper()

    M4A.set_file_paths(path_track_resources)
    assert M4A.available_track_paths == {path_track_m4a}
    assert M4A._available_track_paths_lower_map == {path_track_m4a.lower(): path_track_m4a}

    track = M4A(file=path_track_m4a.upper())
    assert track.path != path_track_m4a.upper()


def test_loaded_attributes():
    track = M4A(file=path_track_m4a)

    # metadata
    assert track.title == 'title 3'
    assert track.artist == 'artist 3'
    assert track.album == 'album artist 3'
    assert track.album_artist == 'various'
    assert track.track_number == 2
    assert track.track_total == 4
    assert track.genres == ['Dance', 'Techno']
    assert track.year == 2021
    assert track.bpm == 120.0
    assert track.key == 'B'
    assert track.disc_number == 1
    assert track.disc_total == 2
    assert track.compilation
    assert track.comments == ['spotify:track:4npv0xZO9fVLBmDS2XP9Bw']

    assert track.uri == track.comments[0]
    assert track.has_uri

    assert track.image_links is None
    assert track.has_image

    # file properties
    assert track.path == path_track_m4a
    assert track.folder == basename(dirname(path_track_m4a))
    assert track.filename == basename(path_track_m4a)
    assert track.ext == '.m4a'
    assert track.size == 302199
    assert int(track.length) == 20
    assert track.date_modified == datetime(2023, 5, 1, 10, 23, 3, 839000)

    # library properties
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None
    assert track.rating is None


def test_cleared_tags():
    track = M4A(file=path_track_m4a)
    clear_tags_test(track)


def test_updated_tags():
    track = M4A(file=path_track_m4a)
    update_tags_test(track)


def test_updated_images():
    track = M4A(file=path_track_m4a)
    update_images_test(track)
