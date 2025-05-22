import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.model import MusifyModel
from musify.model.properties.name import HasName
from tests.model.testers import MusifyResourceTester


class TestHasName(MusifyResourceTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return HasName(name="Test Name")

    def test_from_name(self, adapter: TypeAdapter, faker: Faker):
        name = faker.word()
        model = adapter.validate_python(name)
        assert model.name == name

    def test_rich_comparison_dunder_methods(self) -> None:
        assert HasName(name="Test Name") < HasName(name="Zest Name")
        assert HasName(name="Test Name") <= HasName(name="Zest Name")
        assert HasName(name="Test Name") > HasName(name="Rest Name")
        assert HasName(name="Test Name") >= HasName(name="Rest Name")
