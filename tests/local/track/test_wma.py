from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname, splitext, getmtime

import pytest

from syncify.local.exception import IllegalFileTypeError
from syncify.local.track import WMA
from syncify.spotify import __UNAVAILABLE_URI_VALUE__
from tests.common import path_txt
from tests.local.track.track import path_track_wma, path_track_resources
from tests.local.track.track import update_tags_test, clear_tags_test


def test_load():
    track = WMA(file=path_track_wma)

    track_file = track.file

    track._file = track.get_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    # has actually reloaded the file in each reload
    assert id(track_file) != id(track_reload_1) != id(track_reload_2)

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        WMA(path_txt)

    # raises error on files that do not exist
    with pytest.raises(FileNotFoundError):
        WMA("does_not_exist.wma")


def test_copy():
    track = WMA(file=path_track_wma)

    track_from_file = WMA(file=track.file)
    assert id(track.file) == id(track_from_file.file)

    track_copy = copy(track)
    assert id(track.file) == id(track_copy.file)
    for key, value in vars(track).items():
        assert value == track_copy[key]

    track_deepcopy = deepcopy(track)
    assert id(track.file) != id(track_deepcopy.file)
    for key, value in vars(track).items():
        assert value == track_deepcopy[key]


def test_set_and_find_file_paths():
    track = WMA(file=path_track_wma.upper())
    assert track.path == path_track_wma.upper()

    paths = WMA.get_filepaths(path_track_resources)
    assert paths == {path_track_wma}

    track = WMA(file=path_track_wma.upper(), available=paths)
    assert track.path != path_track_wma.upper()


def test_loaded_attributes():
    track = WMA(file=path_track_wma)

    # metadata
    assert track.title == "title 4"
    assert track.artist == "artist 4"
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
    assert track.comments == [__UNAVAILABLE_URI_VALUE__]

    assert track.uri is None
    assert not track.has_uri

    assert track.image_links == {}
    assert track.has_image

    # file properties
    assert track.path == path_track_wma
    assert track.folder == basename(dirname(path_track_wma))
    assert track.filename == splitext(basename(path_track_wma))[0]
    assert track.ext == ".wma"
    assert track.size == 1193637
    assert int(track.length) == 32
    assert track.date_modified == datetime.fromtimestamp(getmtime(path_track_wma))

    # library properties
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None
    assert track.rating is None


def test_cleared_tags():
    track = WMA(file=path_track_wma)
    clear_tags_test(track)


def test_updated_tags():
    track = WMA(file=path_track_wma)
    update_tags_test(track)


# def test_updated_images():
#     track = WMA(file=path_track_wma)
#     update_images_test(track)
