from random import choice
from typing import Any
from unittest import mock

import pydantic
import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.model import MusifyResource, MusifySequence, MusifyMutableSequence
from musify.model.item.artist import Artist
from musify.model.item.track import Track


class TestMusifySequence:
    @pytest.fixture
    def sequence(self, models: list[MusifyResource]) -> MusifySequence:
        sequence = MusifySequence(models)
        assert sequence._items
        return sequence

    def test_validate_pydantic_schema(self, sequence: MusifySequence, models: list[MusifyResource], faker: Faker) -> None:
        adapter = TypeAdapter(MusifySequence)

        assert adapter.validate_python(sequence) is sequence, "Failed to validate existing model"

        sequence_single = MusifySequence([models[0]])
        assert adapter.validate_python(models[0]) == sequence_single, "Failed to validate single model"
        assert adapter.validate_python(models) == sequence, "Failed to validate list of models"
        assert adapter.validate_python(tuple(models)) == sequence, "Failed to validate tuple of models"

    def test_validate_pydantic_schema_on_generics(self, tracks: list[Track], artists: list[Artist]) -> None:
        adapter = TypeAdapter(MusifySequence[Any, Track])
        assert adapter.validate_python(tracks) == MusifySequence(tracks), "Failed to validate list of tracks"

        with pytest.raises(ValueError):
            adapter.validate_python(artists)

    def test_init(self, sequence: MusifySequence, models: list[MusifyResource], faker: Faker) -> None:
        assert MusifySequence(sequence) is not sequence
        assert MusifySequence(sequence) == sequence

        assert MusifySequence(models) == sequence, "Failed to construct from list of models"
        assert MusifySequence(models).items == models, "Failed to construct from list of models"
        assert MusifySequence(iter(models)) == sequence, "Failed to construct from iterable of models"
        assert MusifySequence(iter(models)).items == models, "Failed to construct from iterable of models"
        mapping = {faker.word(): model for model in models}
        assert MusifySequence(mapping) == sequence, "Failed to construct from mapping of models"
        assert MusifySequence(mapping).items == models, "Failed to construct from mapping of models"

    # noinspection PyTypeChecker
    @pytest.mark.skipif(
        tuple(map(int, pydantic.__version__.split("."))) < (2, 12, 0),
        reason="Pydantic 2.12.0+ required as lower versions do not support generics validation as expected"
        # https://github.com/pydantic/pydantic/issues/7796
    )
    def test_validates_generic_types_when_accessing(self, tracks: list[Track], artists: list[Artist]) -> None:
        sequence = MusifySequence[int, Track](tracks)

        with pytest.raises(ValueError):
            assert choice(artists) in sequence
        with pytest.raises(ValueError):
            assert sequence[choice(artists)]

        with pytest.raises(ValueError):
            assert sequence.intersection(artists)
        with pytest.raises(ValueError):
            assert sequence.difference(artists)
        with pytest.raises(ValueError):
            assert sequence.outer_difference(artists)

    def test_container_methods(self, sequence: MusifySequence, models: list[MusifyResource]) -> None:
        assert choice(models) in sequence
        assert all(key in sequence for key in choice(models).unique_keys)

        assert sequence._items in sequence
        assert (key for model in sequence._items for key in model.unique_keys) in sequence

    def test_collection_methods(self, sequence: MusifySequence, models: list[MusifyResource]) -> None:
        assert len(sequence) == len(models)
        assert list(iter(sequence)) == sequence._items

    def test_equality(self, sequence: MusifySequence, models: list[MusifyResource]):
        assert sequence is not MusifySequence(models)
        assert sequence == MusifySequence(models)

        models_initial = models[2:]
        assert sequence != MusifySequence(models_initial)
        assert MusifySequence(models_initial) != sequence

    def test_copy(self, sequence: MusifySequence, models: list[MusifyResource]):
        sequence_copy = sequence.copy()
        assert isinstance(sequence_copy, sequence.__class__)
        assert sequence_copy is not sequence
        assert sequence_copy._items is not sequence._items
        assert sequence_copy._items == sequence._items

    def test_getitem(self, sequence: MusifySequence, models: list[MusifyResource]):
        assert sequence[0] == models[0]
        assert sequence[:2] == models[:2]
        assert sequence[next(iter(models[0].unique_keys))] == models[0]

    def test_getitem_fails(self, sequence: MusifySequence, models: list[MusifyResource]):
        models_initial = models[2:]
        sequence = MusifySequence(models_initial)

        with pytest.raises(KeyError):
            assert sequence[next(iter(models[0].unique_keys))]
        with pytest.raises(KeyError):
            assert sequence["unknown"]

    @staticmethod
    def test_intersection(models: list[MusifyResource]):
        index = len(models) // 2
        models_initial, models_other = tuple(models[index:]), tuple(models[:index])
        sequence = MusifySequence(models_initial)

        assert sequence.intersection(models_initial) == models_initial
        assert sequence.intersection(models_other) == ()
        assert sequence.intersection(models_other + models_initial[2:]) == models_initial[2:]

    @staticmethod
    def test_difference(models: list[MusifyResource]):
        index = len(models) // 2
        models_initial, models_other = tuple(models[index:]), tuple(models[:index])
        sequence = MusifySequence(models_initial)

        assert sequence.difference(models_initial) == ()
        assert sequence.difference(models_other) == models_initial
        assert sequence.difference(models_other + models_initial[2:]) == models_initial[:2]

    @staticmethod
    def test_outer_difference(models: list[MusifyResource]):
        index = len(models) // 2
        models_initial, models_other = tuple(models[index:]), tuple(models[:index])
        sequence = MusifySequence(models_initial)

        assert sequence.outer_difference(models_initial) == ()
        assert sequence.outer_difference(models_other) == models_other
        assert sequence.outer_difference(models_other + models_initial[2:]) == models_other


class TestMusifyMutableSequence:
    # noinspection PyTypeChecker
    @pytest.mark.skipif(
        tuple(map(int, pydantic.__version__.split("."))) < (2, 12, 0),
        reason="Pydantic 2.12.0+ required as lower versions do not support generics validation as expected"
        # https://github.com/pydantic/pydantic/issues/7796
    )
    def test_validates_generic_types_when_mutating(self, tracks: list[Track], artists: list[Artist]) -> None:
        sequence = MusifyMutableSequence[int, Track](tracks)

        with pytest.raises(ValueError):
            sequence[0] = choice(artists)
        with pytest.raises(ValueError):
            sequence + artists
        with pytest.raises(ValueError):
            sequence += artists
        with pytest.raises(ValueError):
            sequence - artists
        with pytest.raises(ValueError):
            sequence -= artists

        with pytest.raises(ValueError):
            sequence.append(choice(artists))
        with pytest.raises(ValueError):
            sequence.extend(artists)
        with pytest.raises(ValueError):
            sequence.insert(0, choice(artists))
        with pytest.raises(ValueError):
            sequence.remove(choice(artists))

    def test_setitem(self, models: list[MusifyResource]) -> None:
        index = len(models) // 2
        models_initial, models_other = models[index:], models[:index]
        sequence = MusifyMutableSequence(models_initial)

        model = choice(models_other)
        assert model not in sequence

        sequence[0] = model
        assert model in sequence
        assert sequence._items[0] == model
        assert all(key in sequence._items_mapped for key in model.unique_keys)

        sequence[0:2] = models_initial[1:3]
        assert all(m in sequence for m in models_initial[1:3])
        assert sequence._items[0:2] == models_initial[1:3]
        assert all(key in sequence._items_mapped for m in models_initial[1:3] for key in m.unique_keys)

    def test_setitem_fails(self, models: list[MusifyResource]) -> None:
        models_initial = models[:3]
        sequence = MusifyMutableSequence(models_initial)

        with pytest.raises(ValueError):
            sequence[0] = "invalid value"

    def test_delitem(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models)
        model = models[0]
        assert model in sequence

        del sequence[sequence._items.index(model)]
        assert model not in sequence
        assert all(key not in sequence._items_mapped for key in model.unique_keys)

        del sequence[0:2]
        assert all(model not in sequence for model in models[1:3])
        assert all(key not in sequence._items_mapped for m in models[1:3] for key in m.unique_keys)

    def test_delitem_fails(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence()
        with pytest.raises(KeyError):
            del sequence[0]

    def test_mutable_dunder_methods(self, models: list[MusifyResource]) -> None:
        index = len(models) // 2
        models_initial, models_other = models[index:], models[:index]
        sequence = MusifyMutableSequence(models_initial)
        original = sequence.copy()

        assert sequence + sequence == sequence._items + sequence._items
        assert sequence - sequence == []
        assert sequence._items == original._items
        assert sequence._items_mapped == original._items_mapped

        sequence += models_other
        assert len(sequence) == len(original) + len(models_other)
        assert sequence._items != original._items
        assert sequence._items_mapped != original._items_mapped
        assert all(key in sequence._items_mapped for m in models_other for key in m.unique_keys)

        sequence -= original
        assert len(sequence) == len(models_other)
        assert sequence._items == models_other
        assert all(key in sequence._items_mapped for m in models_other for key in m.unique_keys)

    def test_append(self, models: list[MusifyResource]) -> None:
        models_initial = models[3:]
        sequence = MusifyMutableSequence(models_initial)
        original_length = len(sequence._items)

        model = models[0]
        assert model not in sequence

        sequence.append(model)
        assert len(sequence) == original_length + 1
        assert model in sequence
        assert sequence._items[-1] == model
        assert all(key in sequence._items_mapped for key in model.unique_keys)
        expected_keys = set(sequence._items_mapped)

        # adds duplicates
        sequence.append(model)
        assert len(sequence) == original_length + 2
        assert sequence._items[-1] == model
        assert sequence._items[-2] == model
        assert sequence._items_mapped.keys() == expected_keys

    def test_extend(self, models: list[MusifyResource]):
        index = len(models) // 2
        models_initial, models_other = models[index:], models[:index]
        sequence = MusifyMutableSequence(models_initial)
        original_length = len(sequence._items)
        assert all(m not in sequence for m in models_other)

        sequence.extend(models_other)
        assert len(sequence) == original_length + len(models_other)
        assert all(m in sequence for m in models_other)
        assert sequence._items[-len(models_other):] == models_other
        assert all(key in sequence._items_mapped for m in models_other for key in m.unique_keys)
        expected_keys = set(sequence._items_mapped)

        # adds duplicates
        sequence.extend(models_other)
        assert len(sequence) == original_length + 2 * len(models_other)
        assert sequence._items[-len(models_other):] == models_other
        assert sequence._items[-len(models_other) * 2:-len(models_other)] == models_other
        assert sequence._items_mapped.keys() == expected_keys

    def test_insert(self, models: list[MusifyResource]) -> None:
        models_initial = models[3:]
        sequence = MusifyMutableSequence(models_initial)
        original_length = len(sequence._items)

        model = models[0]
        assert model not in sequence

        sequence.insert(2, model)
        assert len(sequence) == original_length + 1
        assert model in sequence
        assert sequence._items[2] == model
        assert all(key in sequence._items_mapped for key in model.unique_keys)
        expected_keys = set(sequence._items_mapped)

        # adds duplicates
        sequence.insert(2, model)
        assert len(sequence) == original_length + 2
        assert sequence._items[2] == model
        assert sequence._items[3] == model
        assert sequence._items_mapped.keys() == expected_keys

    def test_remove(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models)
        model = choice(models)
        assert model in sequence

        sequence.remove(model)
        assert model not in sequence._items
        assert all(key not in sequence._items_mapped for key in model.unique_keys)

    def test_clear(self, models: list[MusifyResource]):
        models_initial = models[3:]
        sequence = MusifyMutableSequence(models_initial)
        assert sequence._items
        assert sequence._items_mapped

        sequence.clear()
        assert not sequence._items
        assert not sequence._items_mapped
