import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.item.album import Album, HasAlbums
from musify.model.properties.uri import URI
from tests.model.testers import MusifyResourceTester, UniqueKeyTester


class TestAlbum(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return Album(name=faker.word(), uri=uri)


class TestHasAlbums(MusifyResourceTester):
    @pytest.fixture
    def model(self, albums: list[Album]) -> MusifyModel:
        return HasAlbums(albums=albums)

    def test_from_string(self, albums: list[Album]):
        album = HasAlbums._join_tags(album.name for album in albums)
        model = HasAlbums(album=album)
        assert [album.name for album in model.albums] == [album.name for album in albums]
