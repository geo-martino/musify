from abc import ABCMeta

import pytest

from syncify.local.library import LocalLibrary
from tests.local.track.testers import LocalCollectionTester
from tests.shared.core.collection import LibraryTester


class LocalLibraryTester(LibraryTester, LocalCollectionTester, metaclass=ABCMeta):

    @pytest.mark.skip(reason="# TODO: write merge_playlists tests")
    def test_merge_playlists(self, library: LocalLibrary):
        pass
