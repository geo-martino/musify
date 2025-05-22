from abc import ABCMeta, abstractmethod
from collections.abc import Hashable

import pytest
from pydantic import TypeAdapter

from musify.model import MusifyModel, MusifyRootModel, MusifyResource


class MusifyModelTester(metaclass=ABCMeta):
    @abstractmethod
    def model(self, **kwargs) -> MusifyModel | MusifyRootModel:
        """Fixture for the model to test"""
        raise NotImplementedError

    @pytest.fixture
    def adapter(self, model: MusifyModel | MusifyRootModel) -> TypeAdapter:
        """Fixture for the type adapter to use when validating python objects for this model"""
        return TypeAdapter(model.__class__)


class MusifyResourceTester(MusifyModelTester, metaclass=ABCMeta):
    def test_check_unique_key_tester_enabled(self, model: MusifyResource):
        """Test that the unique key tester is enabled"""
        if model.__unique_attributes__:
            assert isinstance(self, UniqueKeyTester), "Unique keys are configured but UniqueKeyTester is not enabled"
        else:
            assert not isinstance(self, UniqueKeyTester), \
                "Unique keys are not configured but UniqueKeyTester is enabled"

    @staticmethod
    def test_check_unique_keys(model: MusifyResource):
        """Test that the unique keys are set correctly"""
        assert not model.__unique_attributes__, "Unique attributes are not set on the test model"
        assert model.unique_keys == {id(model)}, "ID not found in unique keys"


class UniqueKeyTester(MusifyModelTester, metaclass=ABCMeta):
    @staticmethod
    def test_check_unique_keys(model: MusifyResource):
        """Test that the unique keys are set correctly"""
        assert model.__unique_attributes__, "Unique attributes are not set on the test model"
        assert len(model.unique_keys) > 1, "Unique keys not found"

        for key in model.__unique_attributes__:
            if (value := getattr(model, key, None)) is None:
                assert None not in model.unique_keys, "Unique keys should not contain None"
                continue

            assert value in model.unique_keys, f"Value {value} not found in unique keys"
            assert isinstance(value, Hashable)

            try:
                setattr(model, key, None)
                assert value not in model.unique_keys, f"Value {value} should not be in unique keys after removing it"
            except (AttributeError, ValueError):  # value is not mutable or nullable
                pass
