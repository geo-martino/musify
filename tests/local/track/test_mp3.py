from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname, splitext

import pytest

from syncify.local.track import MP3
from syncify.local.file import IllegalFileTypeError
from tests.common import path_txt
from tests.local.track.track import path_track_mp3, path_track_resources
from tests.local.track.track import update_tags_test, clear_tags_test, update_images_test


def test_load():
    track = MP3(file=path_track_mp3)

    track_file = track.file

    track.load_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    # has actually reloaded the file in each reload
    assert id(track_file) != id(track_reload_1) != id(track_reload_2)

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        MP3(path_txt)

    # raises error on files that do not exist
    with pytest.raises(FileNotFoundError):
        MP3("does_not_exist.mp3")


def test_copy():
    track = MP3(file=path_track_mp3)

    track_from_file = MP3(file=track.file)
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
    track = MP3(file=path_track_mp3.upper())
    assert track.path == path_track_mp3.upper()

    paths = MP3.get_filepaths(path_track_resources)
    assert paths == {path_track_mp3}

    track = MP3(file=path_track_mp3.upper(), available=paths)
    assert track.path != path_track_mp3.upper()


def test_loaded_attributes():
    track = MP3(file=path_track_mp3)

    # metadata
    assert track.title == 'title 2'
    assert track.artist == 'artist 2'
    assert track.album == 'album artist 2'
    assert track.album_artist == 'various'
    assert track.track_number == 3
    assert track.track_total == 4
    assert track.genres == ['Pop Rock', 'Musical']
    assert track.year == 2024
    assert track.bpm == 200.56
    assert track.key == 'C'
    assert track.disc_number == 2
    assert track.disc_total == 3
    assert not track.compilation
    # noinspection SpellCheckingInspection
    assert track.comments == ['spotify:track:1TjVbzJUAuOvas1bL00TiH']

    assert track.uri == track.comments[0]
    assert track.has_uri

    assert track.image_links is None
    assert track.has_image

    # file properties
    assert track.path == path_track_mp3
    assert track.folder == basename(dirname(path_track_mp3))
    assert track.filename == splitext(basename(path_track_mp3))[0]
    assert track.ext == '.mp3'
    assert track.size == 411038
    assert int(track.length) == 30
    assert track.date_modified == datetime(2023, 5, 1, 14, 24, 29, 250378)

    # library properties
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None
    assert track.rating is None


def test_cleared_tags():
    track = MP3(file=path_track_mp3)
    clear_tags_test(track)


def test_updated_tags():
    track = MP3(file=path_track_mp3)
    update_tags_test(track)


def test_updated_images():
    track = MP3(file=path_track_mp3)
    update_images_test(track)
