from random import choice
from typing import Any

import pydantic
import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.exception import MusifyKeyError, MusifyValueError
from musify.model import MusifyMapping, MusifyResource, MusifyMutableMapping
from musify.model.item.artist import Artist
from musify.model.item.track import Track

class TestMusifyMapping:
    @pytest.fixture
    def mapping(self, models: list[MusifyResource]) -> MusifyMapping:
        mapping = MusifyMapping({key: model for model in models for key in model.unique_keys})
        assert mapping._items
        return mapping

    def test_validate_pydantic_schema(self, mapping: MusifyMapping, models: list[MusifyResource], faker: Faker) -> None:
        adapter = TypeAdapter(MusifyMapping)

        assert adapter.validate_python(mapping) is mapping, "Failed to validate existing model"

        mapping_single = MusifyMapping({key: models[0] for key in models[0].unique_keys})
        assert adapter.validate_python(models[0]) == mapping_single, "Failed to validate single model"
        assert adapter.validate_python(models) == mapping, "Failed to validate list of models"
        assert adapter.validate_python(tuple(models)) == mapping, "Failed to validate tuple of models"
        assert adapter.validate_python({faker.word(): model for model in models}) == mapping, \
            "Failed to ignore keys in mapping"

    def test_validate_pydantic_schema_on_generics(self, tracks: list[Track], artists: list[Artist]) -> None:
        adapter = TypeAdapter(MusifyMapping[Any, Track])
        assert adapter.validate_python(tracks) == MusifyMapping(tracks), "Failed to validate list of tracks"

        with pytest.raises(ValueError):
            adapter.validate_python(artists)

    def test_init(self, mapping: MusifyMapping, models: list[MusifyResource], faker: Faker) -> None:
        assert MusifyMapping(mapping) is not mapping
        assert MusifyMapping(mapping) == mapping

        assert MusifyMapping(models) == mapping, "Failed to construct from list of models"
        assert MusifyMapping(iter(models)) == mapping, "Failed to construct from iterable of models"

    # noinspection PyTypeChecker
    @pytest.mark.skipif(
        tuple(map(int, pydantic.__version__.split("."))) < (2, 12, 0),
        reason="Pydantic 2.12.0+ required as lower versions do not support generics validation as expected"
        # https://github.com/pydantic/pydantic/issues/7796
    )
    def test_validates_generic_types_when_accessing(self, tracks: list[Track], artists: list[Artist]) -> None:
        mapping = MusifyMapping[int, Track](tracks)

        with pytest.raises(ValueError):
            assert choice(artists) in mapping
        with pytest.raises(ValueError):
            assert mapping[choice(artists)]

    def test_container_methods(self, mapping: MusifyMapping, models: list[MusifyResource]) -> None:
        assert choice(models) in mapping
        assert all(key in mapping for key in choice(models).unique_keys)

        assert mapping.values() in mapping
        assert (key for model in mapping.values() for key in model.unique_keys) in mapping

    def test_collection_methods(self, mapping: MusifyMapping, models: list[MusifyResource]) -> None:
        assert len(mapping) == len(models)
        assert list(iter(mapping)) == list(mapping._items.keys())

    def test_equality(self, mapping: MusifyMapping, models: list[MusifyResource]):
        assert mapping is not MusifyMapping(models)
        assert mapping == MusifyMapping(models)

        models_initial = models[2:]
        assert mapping != MusifyMapping(models_initial)
        assert MusifyMapping(models_initial) == mapping

    def test_copy(self, mapping: MusifyMapping, models: list[MusifyResource]):
        mapping_copy = mapping.copy()
        assert isinstance(mapping_copy, mapping.__class__)
        assert mapping_copy is not mapping
        assert mapping_copy._items is not mapping._items
        assert mapping_copy._items == mapping._items

    def test_getitem(self, mapping: MusifyMapping, models: list[MusifyResource]):
        model = models[0]
        assert mapping[model] == model
        assert mapping[next(iter(model.unique_keys))] == model

    def test_getitem_fails(self, mapping: MusifyMapping, models: list[MusifyResource]):
        models_initial = models[2:]
        mapping = MusifyMapping(models_initial)

        with pytest.raises(MusifyKeyError):
            assert mapping[models[0]]
        with pytest.raises(KeyError):
            assert mapping["unknown"]


class TestMusifyMutableMapping:
    # noinspection PyTypeChecker
    @pytest.mark.skipif(
        tuple(map(int, pydantic.__version__.split("."))) < (2, 12, 0),
        reason="Pydantic 2.12.0+ required as lower versions do not support generics validation as expected"
        # https://github.com/pydantic/pydantic/issues/7796
    )
    def test_validates_generic_types_when_mutating(self, tracks: list[Track], artists: list[Artist]) -> None:
        mapping = MusifyMutableMapping[int, Track](tracks)

        with pytest.raises(ValueError):
            mapping["key"] = choice(tracks)
        with pytest.raises(ValueError):
            mapping[0] = choice(artists)
        with pytest.raises(ValueError):
            del mapping["key"]

        with pytest.raises(ValueError):
            mapping.add(choice(artists))
        with pytest.raises(ValueError):
            mapping.update(artists)
        with pytest.raises(ValueError):
            mapping.update({id(artist): artist for artist in artists})
        with pytest.raises(ValueError):
            mapping.remove(choice(artists))

    def test_setitem(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping()
        assert len(mapping) == 0
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

        with pytest.raises(ValueError):
            mapping[choice(list(model.unique_keys))] = "invalid value"

    def test_delitem(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping(models)
        model = choice(models)
        assert model in mapping

        del mapping[choice(list(model.unique_keys))]
        assert model not in mapping
        assert all(key not in mapping._items for key in model.unique_keys)

    def test_delitem_fails(self, models: list[MusifyResource]) -> None:
        mapping = MusifyMutableMapping()
        with pytest.raises(KeyError):
            del mapping[choice(models)]

    def test_add(self, models: list[MusifyResource]) -> None:
        models_initial = models[2:]
        mapping = MusifyMutableMapping(models_initial)
        assert len(mapping) == len(models_initial)

        model = models[0]
        assert all(key not in mapping._items for key in model.unique_keys)

        mapping.add(model)
        assert model in mapping
        assert all(key in mapping._items for key in model.unique_keys)
        assert len(mapping) == len(models_initial) + 1

        # unchanged when adding existing resource
        mapping.add(choice(list(mapping.values())))
        assert len(mapping) == len(models_initial) + 1

    def test_add_fails(self, models: list[MusifyResource]) -> None:
        models_initial = models[2:]
        mapping = MusifyMutableMapping(models_initial)

        with pytest.raises(ValueError):
            mapping.add("invalid value")

    def test_update(self, models: list[MusifyResource]):
        models_initial = models[2:]
        mapping = MusifyMutableMapping(models_initial)
        assert not all(key in mapping._items for model in models for key in model.unique_keys)
        assert len(mapping) < len(models)

        mapping.update(models)
        assert all(key in mapping._items for model in models for key in model.unique_keys)
        assert len(mapping) == len(models)

    def test_remove(self, models: list[MusifyResource]):
        models_initial = models[2:]
        mapping = MusifyMutableMapping(models_initial)
        assert len(mapping) == len(models_initial)

        model = choice(list(mapping.values()))
        assert model in mapping

        mapping.remove(model)
        assert model not in mapping
        assert all(key not in mapping._items for key in model.unique_keys)
        assert len(mapping) == len(models_initial) - 1

        # doesn't fail when removing non-existing resource
        assert models[0] not in mapping
        mapping.remove(models[0])

    def test_clear(self, models: list[MusifyResource]):
        models_initial = models[2:]
        mapping = MusifyMutableMapping(models_initial)
        assert mapping._items

        mapping.clear()
        assert not mapping._items
