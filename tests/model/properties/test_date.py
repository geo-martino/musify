from datetime import date

import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.model import MusifyModel
from musify.model.properties.date import SparseDate
from tests.model.testers import MusifyModelTester


class TestSparseDate(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return SparseDate(year=faker.year())

    def test_from_date(self, adapter: TypeAdapter):
        model = adapter.validate_python("2025-03-01")
        assert model.year == 2025
        assert model.month == 3
        assert model.day == 1

        model = adapter.validate_python(date(2025, 3, 1))
        assert model.year == 2025
        assert model.month == 3
        assert model.day == 1

    def test_from_string(self, adapter: TypeAdapter):
        model = adapter.validate_python("2025-03")
        assert model.year == 2025
        assert model.month == 3
        assert model.day is None

        model = adapter.validate_python("2025")
        assert model.year == 2025
        assert model.month is None
        assert model.day is None

    def test_date_property(self, model: SparseDate, faker: Faker) -> None:
        model.month = None
        model.day = None
        assert model.date is None

        model.day = faker.random_int(min=1, max=28)
        assert model.date is None

        model.month = faker.random_int(min=1, max=12)
        assert model.date == date(year=model.year, month=model.month, day=model.day)

    def test_equality(self):
        model = SparseDate(year=2024, month=3, day=12)

        assert model == model
        assert model == date(2024, 3, 12)
        assert model == "2024-03-12"
