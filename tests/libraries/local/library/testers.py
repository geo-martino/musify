from abc import ABCMeta

from tests.libraries.core.collection import LibraryTester
from tests.libraries.local.track.testers import LocalCollectionTester


class LocalLibraryTester(LibraryTester, LocalCollectionTester, metaclass=ABCMeta):
    pass
