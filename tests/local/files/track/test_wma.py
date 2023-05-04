from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname

import pytest

from syncify.local.files import WMA, IllegalFileTypeError
from syncify.spotify.helpers import __UNAVAILABLE_URI_VALUE__
from tests.common import path_file_wma, path_resources, path_file_txt
from tests.local.files.track.track import update_tags_test, clear_tags_test


def test_load():
    track = WMA(file=path_file_wma)

    track_file = track.file

    track.load_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    # has actually reloaded the file in each reload
    assert id(track_file) != id(track_reload_1) != id(track_reload_2)

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        WMA(path_file_txt)

    # raises error on files that do not exist
    with pytest.raises(FileNotFoundError):
        WMA("does_not_exist.wma")


def test_copy():
    track = WMA(file=path_file_wma)

    track_from_file = WMA(file=track.file)
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
    track = WMA(file=path_file_wma.upper())
    assert track.path == path_file_wma.upper()

    WMA.set_file_paths(path_resources)
    assert WMA.available_track_paths == {path_file_wma}
    assert WMA._available_track_paths_lower_map == {path_file_wma.lower(): path_file_wma}

    track = WMA(file=path_file_wma.upper())
    assert track.path != path_file_wma.upper()


def test_loaded_attributes():
    track = WMA(file=path_file_wma)

    # metadata
    assert track.title == 'title 4'
    assert track.artist == 'artist 4'
    assert track.album == 'album artist 4'
    assert track.album_artist == 'various'
    assert track.track_number == 4
    assert track.track_total == 4
    assert track.genres == ['Metal', 'Rock']
    assert track.year == 2023
    assert track.bpm == 200.56
    assert track.key == 'D'
    assert track.disc_number == 3
    assert track.disc_total == 4
    assert not track.compilation
    assert track.comments == [__UNAVAILABLE_URI_VALUE__]

    assert track.uri is None
    assert not track.has_uri

    assert track.image_links is None
    assert track.has_image

    # file properties
    assert track.path == path_file_wma
    assert track.folder == basename(dirname(path_file_wma))
    assert track.filename == basename(path_file_wma)
    assert track.ext == '.wma'
    assert track.size == 1193637
    assert int(track.length) == 32
    assert track.date_modified == datetime(2023, 5, 1, 19, 27, 19, 440000)

    # library properties
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None
    assert track.rating is None


def test_cleared_tags():
    track = WMA(file=path_file_wma)
    clear_tags_test(track)


def test_updated_tags():
    track = WMA(file=path_file_wma)
    update_tags_test(track)
