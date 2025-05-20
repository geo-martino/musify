from collections.abc import MutableMapping
from random import choice

import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.exception import MusifyKeyError, MusifyValueError
from musify.model import MusifyMapping, MusifyResource, MusifyMutableMapping


class TestMusifyMapping:
    @pytest.fixture
    def mapping(self, models: list[MusifyResource]) -> MusifyMapping:
        mapping = MusifyMapping({key: model for model in models for key in model.unique_keys})
        assert mapping.items
        return mapping

    def test_validate_pydantic_schema(self, mapping: MusifyMapping, models: list[MusifyResource], faker: Faker) -> None:
        adapter = TypeAdapter(MusifyMapping)

        assert adapter.validate_python(mapping) is mapping, "Failed to validate existing model"

        mapping_single = MusifyMapping({key: models[0] for key in models[0].unique_keys})
        assert adapter.validate_python(models[0]) == mapping_single, "Failed to validate single model"
        assert adapter.validate_python(models) == mapping, "Failed to validate list of models"
        assert adapter.validate_python(iter(models)) == mapping, "Failed to validate iterable of models"
        assert adapter.validate_python({faker.word(): model for model in models}) == mapping, \
            "Failed to ignore keys in mapping"

    def test_init(self, mapping: MusifyMapping, models: list[MusifyResource], faker: Faker) -> None:
        assert MusifyMapping(mapping) is not mapping
        assert MusifyMapping(mapping) == mapping

        assert MusifyMapping(models) == mapping, "Failed to construct from list of models"
        assert MusifyMapping(iter(models)) == mapping, "Failed to construct from iterable of models"

    def test_repr(self, mapping: MusifyMapping) -> None:
        assert repr(mapping) == repr(mapping.items)

    def test_container_methods(self, mapping: MusifyMapping, models: list[MusifyResource]) -> None:
        assert choice(models) in mapping
        assert all(key in mapping for key in choice(models).unique_keys)

    def test_collection_methods(self, mapping: MusifyMapping, models: list[MusifyResource]) -> None:
        assert len(mapping) == len(models)
        assert list(iter(mapping)) == list(mapping.items.keys())

    def test_equality(self, mapping: MusifyMapping, models: list[MusifyResource]):
        assert mapping is not MusifyMapping(models)
        assert mapping == MusifyMapping(models)
        assert mapping != MusifyMapping(models[:2])
        assert MusifyMapping(models[:2]) == mapping

    def test_copy(self, mapping: MusifyMapping, models: list[MusifyResource]):
        mapping_copy = mapping.copy()
        assert isinstance(mapping_copy, mapping.__class__)
        assert mapping_copy is not mapping
        assert mapping_copy.items is not mapping.items
        assert mapping_copy.items == mapping.items

    def test_getitem(self, mapping: MusifyMapping, models: list[MusifyResource]):
        assert mapping[models[0]] == models[0]
        assert mapping[next(iter(models[0].unique_keys))] == models[0]

    def test_getitem_fails(self, mapping: MusifyMapping, models: list[MusifyResource]):
        mapping = MusifyMapping(models[2:])
        with pytest.raises(MusifyKeyError):
            assert mapping[models[0]]
        with pytest.raises(KeyError):
            assert mapping["unknown"]


class TestMusifyMutableMapping:
    def test_setitem(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping()
        model = choice(models)

        mapping[choice(list(model.unique_keys))] = model
        assert model in mapping
        assert len(mapping) == 1

        # unchanged when setting for existing resource
        mapping[choice(list(model.unique_keys))] = model
        assert model in mapping
        assert len(mapping) == 1

    def test_setitem_fails(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping()
        model = choice(models)

        with pytest.raises(MusifyValueError):
            mapping[choice(list(model.unique_keys))] = "invalid value"

    def test_delitem_on_key(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping(models)
        model = choice(models)
        assert model in mapping

        del mapping[choice(list(model.unique_keys))]
        assert model not in mapping
        assert all(key not in mapping for key in model.unique_keys)

    def test_delitem_on_resource(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping(models)
        model = choice(models)
        assert model in mapping

        del mapping[model]
        assert model not in mapping
        assert all(key not in mapping for key in model.unique_keys)

    def test_add(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping(models[2:])

        mapping.add(models[0])
        assert models[0] in mapping
        assert all(key in mapping for key in models[0].unique_keys)
        assert len(mapping) == len(models[2:]) + 1

        # unchanged when adding existing resource
        mapping.add(choice(list(mapping.values())))
        assert len(mapping) == len(models[2:]) + 1

    def test_add_fails(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping(models[2:])
        model = models[2]

        with pytest.raises(MusifyValueError):
            mapping.add("invalid value")

    def test_update(self, models: list[MusifyResource]):
        mapping = MusifyMutableMapping(models[2:])
        assert not all(model in mapping for model in models)

        mapping.update(models)
        assert all(model in mapping for model in models)
        assert len(mapping) == len(models)

    def test_remove(self, models: list[MusifyResource]):
        mapping = MusifyMutableMapping(models[2:])
        model = choice(list(mapping.values()))
        assert model in mapping

        mapping.remove(model)
        assert model not in mapping
        assert all(key not in mapping for key in model.unique_keys)
        assert len(mapping) == len(models[2:]) - 1

    def test_remove_fails(self, models: list[MusifyResource]):
        mapping = MusifyMutableMapping(models[2:])
        model = models[0]

        with pytest.raises(MusifyKeyError):
            mapping.remove(model)
        with pytest.raises(KeyError):
            mapping.remove(choice(list(model.unique_keys)))

    def test_clear(self, models: list[MusifyResource]):
        mapping = MusifyMutableMapping(models[2:])
        assert mapping.items

        mapping.clear()
        assert not mapping.items
