from abc import ABC

from tests.libraries.core.collection import LibraryTester
from tests.libraries.local.track.testers import LocalCollectionTester


class LocalLibraryTester(LibraryTester, LocalCollectionTester, ABC):
    pass
