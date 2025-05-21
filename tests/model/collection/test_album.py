import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.album import AlbumCollection
from tests.model.testers import MusifyResourceTester


class TestAlbumCollection(MusifyResourceTester):

    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        print(AlbumCollection(name=faker.word()))
        return AlbumCollection(name=faker.word())
