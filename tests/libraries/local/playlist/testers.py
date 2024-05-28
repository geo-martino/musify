import asyncio
from abc import ABCMeta

import pytest

from musify.libraries.local.track import LocalTrack, load_track
from tests.libraries.core.collection import PlaylistTester
from tests.libraries.local.track.testers import LocalCollectionTester
from tests.libraries.local.utils import path_track_all


class LocalPlaylistTester(PlaylistTester, LocalCollectionTester, metaclass=ABCMeta):

    @pytest.fixture(scope="class")
    async def tracks(self) -> list[LocalTrack]:
        """Yield list of all real LocalTracks"""
        return list(await asyncio.gather(*[await load_track(path) for path in path_track_all]))
