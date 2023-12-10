from abc import ABCMeta
from collections.abc import Iterable
from random import randrange

import pytest

from syncify.local.track import LocalTrack, FLAC, M4A, MP3, WMA
from tests.abstract.collection import ItemCollectionTester
from tests.local.track import path_track_flac, path_track_m4a, path_track_wma, path_track_mp3
from tests.local.track import random_tracks


class LocalPlaylistTester(ItemCollectionTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`LocalPlaylist` implementations"""

    @staticmethod
    @pytest.fixture
    def collection_merge_items() -> Iterable[LocalTrack]:
        return random_tracks(randrange(5, 10))

    @staticmethod
    @pytest.fixture(scope="module")
    def tracks() -> list[LocalTrack]:
        """Yield list of all real LocalTracks"""
        return [
            FLAC(file=path_track_flac), WMA(file=path_track_wma), M4A(file=path_track_m4a), MP3(file=path_track_mp3)
        ]
