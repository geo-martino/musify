from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname

from common import path_file_flac, path_root, path_resources
from local.files.flac import FLAC


def test_load():
    track = FLAC(file=path_file_flac)

    track_file = track.file

    track.load_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    assert id(track_file) != id(track_reload_1) != id(track_reload_2)


def test_copy():
    track = FLAC(file=path_file_flac)

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


def test_set_file_paths():
    track = FLAC(file=path_file_flac.upper())
    assert track.path == path_file_flac.upper()

    FLAC.set_file_paths(path_resources)
    assert FLAC._filepaths == [path_file_flac]

    track = FLAC(file=path_file_flac.upper())
    assert track.path != path_file_flac.upper()


def test_loaded_attributes():
    track = FLAC(file=path_file_flac, position=1)

    # metadata
    assert track.position == 1
#     assert track.title == ""
#     assert track.artist == ""
#     assert track.album == ""
#     assert track.album_artist == ""
#     assert track.track_number == 0
#     assert track.track_total == 0
#     assert track.genres == []
#     assert track.year == 0
#     assert track.bpm == 0
#     assert track.key == ""
#     assert track.disc_number == 1
#     assert track.disc_total == 1
#     assert not track.compilation
#     assert track.image_urls is None
#     assert not track.has_image
#     assert track.comments == []
#
#     assert track.uri == ""
#     assert not track.has_uri
#
#     # file properties
#     assert track.path == path_file_flac
#     assert track.folder == basename(dirname(path_file_flac))
#     assert track.filename == basename(path_file_flac)
#     assert track.ext == ".flac"
#     assert track.size == 123
#     assert track.length == 20
#     assert track.date_modified == datetime.now()
#
#     # library properties
#     assert track.date_added is None
#     assert track.last_played is None
#     assert track.play_count is None
#     assert track.rating is None

def test_updated_attributes():
    track = FLAC(file=path_file_flac, position=1)
