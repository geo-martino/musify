import pytest
from faker import Faker

from musify.model import MusifyRootModel
from musify.model.properties.length import Length
from tests.model.testers import MusifyModelTester


class TestLength(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyRootModel:
        return Length(faker.random_int())

    def test_numeric_representation_conversion(self, model: Length) -> None:
        model.root = "12"
        assert int(model) == 12

        model.root = "12.3456"
        assert float(model) == 12.3456

        model.root = "12:34"
        assert int(model) == 12 * 60 + 34

        model.root = "260:12:34"
        assert int(model) == 260 * 60 * 60 + 12 * 60 + 34

        model.root = "12:34.123456"
        assert float(model) == 12 * 60 + 34 + 0.123456

    def test_numeric_representation_conversion_fails(self, model: Length) -> None:
        with pytest.raises(ValueError):
            model.root = "12:34:56:78"
        with pytest.raises(ValueError):
            model.root = "ab:cd"

    def test_number_conversion(self, model: Length) -> None:
        model.root = 123.45
        assert int(model) == 123

        model.root = 123
        assert float(model) == 123.0
