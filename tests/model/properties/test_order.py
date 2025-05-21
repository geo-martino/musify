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

    def test_from_number(self, faker: Faker):
        number = faker.random_int(1, 10)
        model = TypeAdapter(Position).validate_python(number)
        assert model.number == number
        assert model.total is None

    def test_number_cannot_exceed_total(self, model: Position) -> None:
        model.total = 5
        with pytest.raises(ValueError):
            model.number = model.total + 1

        with pytest.raises(ValueError):
            Position(number=5, total=4)
