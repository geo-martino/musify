from abc import ABCMeta

import pytest

from musify.libraries.local.library import LocalLibrary
from tests.libraries.core.collection import LibraryTester
from tests.libraries.local.track.testers import LocalCollectionTester


class LocalLibraryTester(LibraryTester, LocalCollectionTester, metaclass=ABCMeta):

    @pytest.mark.skip(reason="not implemented yet")
    def test_merge_playlists(self, library: LocalLibrary):
        pass
