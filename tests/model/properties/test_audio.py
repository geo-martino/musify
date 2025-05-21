import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.properties.audio import KeySignature
from tests.model.testers import MusifyModelTester


class TestKeySignature(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        # noinspection PyProtectedMember
        return KeySignature(
            root=faker.random_int(min=0, max=len(KeySignature._root_notes) - 1),
            mode=faker.boolean(),
        )

    def test_key_property(self, model: KeySignature) -> None:
        model.root = 5
        model.mode = False
        assert model.key == str(model) == "F"

        model.mode = True
        assert model.key == str(model) == "Fm"

    def test_set_by_key_signature(self, model: KeySignature) -> None:
        model.mode = False
        model.root = "Gm"
        assert model.root == 7
        assert not model.mode  # remains unchanged

        model.mode = "Am"
        assert model.root == 7  # remains unchanged
        assert model.mode

        model.key = "Cm"
        assert model.root == 0
        assert model.mode
