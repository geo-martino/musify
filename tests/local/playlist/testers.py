from abc import ABCMeta

from tests.local.track.testers import LocalCollectionTester
from tests.shared.core.collection import PlaylistTester


class LocalPlaylistTester(PlaylistTester, LocalCollectionTester, metaclass=ABCMeta):
    pass
