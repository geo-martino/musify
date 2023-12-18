import pytest

from syncify.local.track import LocalTrack, FLAC, M4A, MP3, WMA
from tests.local.utils import path_track_flac, path_track_m4a, path_track_wma, path_track_mp3


@pytest.fixture(scope="module")
def tracks() -> list[LocalTrack]:
    """Yield list of all real LocalTracks"""
    return [
        FLAC(file=path_track_flac), WMA(file=path_track_wma), M4A(file=path_track_m4a), MP3(file=path_track_mp3)
    ]
