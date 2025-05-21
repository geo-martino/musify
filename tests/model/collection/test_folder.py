import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.folder import Folder
from musify.model.item.album import Album
from musify.model.item.track import Track
from tests.model.testers import MusifyResourceTester
from tests.utils import split_list


class TestFolder(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return Folder(name=faker.word())

    def test_compilation(self, tracks: list[Track]):
        tracks_compilation, tracks_album, _ = split_list(tracks, 2, 5)
        compilation = Album(name="Album 1", compilation=True)
        album = Album(name="Album 2", compilation=False)

        for track in tracks_compilation:
            track.album = compilation
        for track in tracks_album:
            if track in tracks_compilation:
                continue
            track.album = album

        folder = Folder(name="Test Folder", tracks=tracks)
        assert folder.compilation is True

        for track in tracks_compilation:
            if track in tracks_album:
                continue
            track.album = album
        assert folder.compilation is False

    def test_compilation_with_no_albums(self, tracks: list[Track]):
        for track in tracks:
            track.album = None

        folder = Folder(name="Test Folder", tracks=tracks)
        assert folder.compilation is False
