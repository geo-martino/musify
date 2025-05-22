import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.model import MusifyModel
from musify.model.properties.order import Position
from tests.model.testers import MusifyModelTester


class TestPosition(MusifyModelTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return Position()

    # noinspection PyTestUnpassedFixture
    def test_from_number(self, adapter: TypeAdapter, faker: Faker):
        number = faker.random_int(1, 10)
        model = adapter.validate_python(number)
        assert model.number == number
        assert model.total is None

    # noinspection PyTestUnpassedFixture
    def test_from_string(self, adapter: TypeAdapter, faker: Faker):
        numbers = "10"
        model = adapter.validate_python(numbers)
        assert model.number == 10
        assert model.total is None

        numbers = "10/20"
        model = adapter.validate_python(numbers)
        assert model.number == 10
        assert model.total == 20

        numbers = "10/20/30"
        model = adapter.validate_python(numbers)
        assert model.number == 10
        assert model.total == 20

    def test_number_cannot_exceed_total(self, model: Position) -> None:
        model.total = 5
        with pytest.raises(ValueError):
            model.number = model.total + 1

        with pytest.raises(ValueError):
            Position(number=5, total=4)
