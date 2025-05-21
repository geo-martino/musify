import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.album import AlbumCollection
from musify.model.properties.uri import RemoteURI
from tests.model.testers import UniqueKeyTester


class TestAlbumCollection(UniqueKeyTester):

    @pytest.fixture
    def model(self, uri: RemoteURI, faker: Faker) -> MusifyModel:
        return AlbumCollection(name=faker.word(), uri=uri)
