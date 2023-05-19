import pytest

from syncify.local.exception import IllegalFileTypeError
from syncify.local.track import FLAC, M4A, MP3, WMA, load_track
from tests.common import path_txt
from tests.local.track.track import path_track_flac, path_track_mp3, path_track_m4a, path_track_wma


def test_load_track():
    flac = load_track(path_track_flac)
    assert flac.__class__ == FLAC
    assert flac.path == path_track_flac

    mp3 = load_track(path_track_mp3)
    assert mp3.__class__ == MP3
    assert mp3.path == path_track_mp3

    m4a = load_track(path_track_m4a)
    assert m4a.__class__ == M4A
    assert m4a.path == path_track_m4a

    wma = load_track(path_track_wma)
    assert wma.__class__ == WMA
    assert wma.path == path_track_wma

    # raises error on unrecognised file type
    with pytest.raises(IllegalFileTypeError):
        load_track(path_txt)
