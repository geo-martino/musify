from datetime import date

import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.properties.date import SparseDate
from tests.model.testers import MusifyModelTester


class TestSparseDate(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return SparseDate(year=faker.year())

    def test_date_property(self, model: SparseDate, faker: Faker) -> None:
        model.month = None
        model.day = None
        assert model.date is None

        model.day = faker.random_int(min=1, max=28)
        assert model.date is None

        model.month = faker.random_int(min=1, max=12)
        assert model.date == date(year=model.year, month=model.month, day=model.day)
