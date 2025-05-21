import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.item.album import Album, HasAlbums
from musify.model.properties.uri import RemoteURI
from tests.model.testers import MusifyResourceTester, UniqueKeyTester


class TestAlbum(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: RemoteURI, faker: Faker) -> MusifyModel:
        return Album(name=faker.word(), uri=uri)


class TestHasAlbums(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return HasAlbums(albums=[Album(name=faker.word()) for _ in range(faker.random_int(3, 6))])

    def test_from_string(self, faker: Faker):
        albums = [faker.word() for _ in range(faker.random_int(3, 6))]
        model = HasAlbums(album=HasAlbums._join_tags(albums))
        assert [album.name for album in model.albums] == albums
