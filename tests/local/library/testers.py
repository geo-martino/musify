from abc import ABCMeta

import pytest

from syncify.local.library import LocalLibrary
from tests.local.track.testers import LocalCollectionTester
from tests.shared.core.collection import LibraryTester


class LocalLibraryTester(LibraryTester, LocalCollectionTester, metaclass=ABCMeta):

    @pytest.mark.skip(reason="not implemented yet")
    def test_merge_playlists(self, library: LocalLibrary):
        pass
