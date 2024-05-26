from abc import ABCMeta

from tests.libraries.core.collection import PlaylistTester
from tests.libraries.local.track.testers import LocalCollectionTester


class LocalPlaylistTester(PlaylistTester, LocalCollectionTester, metaclass=ABCMeta):
    pass
