from abc import ABC

from tests.libraries.core.collection import PlaylistTester
from tests.libraries.local.track.testers import LocalCollectionTester


class LocalPlaylistTester(PlaylistTester, LocalCollectionTester, ABC):
    pass
