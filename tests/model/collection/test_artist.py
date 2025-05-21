import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.artist import ArtistCollection
from musify.model.item.album import Album
from tests.model.testers import MusifyResourceTester


class TestArtistCollection(MusifyResourceTester):
    @pytest.fixture
    def model(self, albums: list[Album], faker: Faker) -> MusifyModel:
        return ArtistCollection(name=faker.word(), albums=albums)
