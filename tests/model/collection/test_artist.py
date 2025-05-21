import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.artist import ArtistCollection
from musify.model.item.album import Album
from musify.model.properties import RemoteURI
from tests.model.testers import UniqueKeyTester


class TestArtistCollection(UniqueKeyTester):
    @pytest.fixture
    def model(self, albums: list[Album], uri: RemoteURI, faker: Faker) -> MusifyModel:
        return ArtistCollection(name=faker.word(), albums=albums, uri=uri)
