from syncify.local.files.track import load_track, FLAC, M4A, MP3, WMA
from syncify.local.files.utils.exception import IllegalFileTypeError
from tests.common import path_file_flac, path_file_mp3, path_file_m4a, path_file_wma, path_file_txt

import pytest


def test_load_track():
    flac = load_track(path_file_flac)
    assert flac.__class__ == FLAC
    assert flac.path == path_file_flac

    mp3 = load_track(path_file_mp3)
    assert mp3.__class__ == MP3
    assert mp3.path == path_file_mp3

    m4a = load_track(path_file_m4a)
    assert m4a.__class__ == M4A
    assert m4a.path == path_file_m4a

    wma = load_track(path_file_wma)
    assert wma.__class__ == WMA
    assert wma.path == path_file_wma

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        load_track(path_file_txt)
