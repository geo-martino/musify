import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.folder import Folder
from tests.model.testers import MusifyResourceTester


class TestFolder(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return Folder(name=faker.word())
