from abc import ABCMeta, abstractmethod

from musify.model import MusifyModel, MusifyResource


class MusifyModelTester(metaclass=ABCMeta):
    @abstractmethod
    def model(self) -> MusifyModel:
        """Fixture for the model to test"""
        raise NotImplementedError


class MusifyResourceTester(MusifyModelTester, metaclass=ABCMeta):
    def test_check_unique_key_tester_enabled(self, handler: MusifyResource):
        """Test that the unique key tester is enabled"""
        if handler.__unique_attributes__:
            assert isinstance(self, UniqueKeyTester), "Unique keys are configured but UniqueKeyTester is not enabled"
        else:
            assert not isinstance(self, UniqueKeyTester), "Unique keys are not configured but UniqueKeyTester is enabled"


class UniqueKeyTester(MusifyModelTester, metaclass=ABCMeta):
    @staticmethod
    def test_check_unique_keys(model: MusifyResource):
        """Test that the unique keys are set correctly"""
        assert model.__unique_attributes__, "Unique attributes are not set on the test model"
        assert model.unique_keys, "Unique keys are not set on the test model"

        for key in model.__unique_attributes__:
            if (value := getattr(model, key, None)) is None:
                assert None not in model.unique_keys, "Unique keys should not contain None"
                continue

            assert value in model.unique_keys, f"Value {value} not found in unique keys"
            try:
                setattr(model, key, None)
                assert value not in model.unique_keys, f"Value {value} should not be in unique keys after removing it"
            except ValueError:  # value is not nullable
                pass
