from random import choice
from unittest import mock

import pytest
from faker import Faker
from pydantic import TypeAdapter

from musify.exception import MusifyValueError
from musify.model import MusifyResource, MusifySequence, MusifyMutableSequence


class TestMusifySequence:
    @pytest.fixture
    def sequence(self, models: list[MusifyResource]) -> MusifySequence:
        sequence = MusifySequence(models)
        assert sequence.items
        return sequence

    def test_validate_pydantic_schema(self, sequence: MusifySequence, models: list[MusifyResource], faker: Faker) -> None:
        adapter = TypeAdapter(MusifySequence)

        assert adapter.validate_python(sequence) is sequence, "Failed to validate existing model"

        sequence_single = MusifySequence([models[0]])
        assert adapter.validate_python(models[0]) == sequence_single, "Failed to validate single model"
        assert adapter.validate_python(models) == sequence, "Failed to validate list of models"
        assert adapter.validate_python(iter(models)) == sequence, "Failed to validate iterable of models"

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

    def test_container_methods(self, sequence: MusifySequence, models: list[MusifyResource]) -> None:
        assert choice(models) in sequence
        assert all(key in sequence for key in choice(models).unique_keys)

    def test_collection_methods(self, sequence: MusifySequence, models: list[MusifyResource]) -> None:
        assert len(sequence) == len(models)
        assert list(iter(sequence)) == sequence.items

    def test_equality(self, sequence: MusifySequence, models: list[MusifyResource]):
        assert sequence is not MusifySequence(models)
        assert sequence == MusifySequence(models)
        assert sequence != MusifySequence(models[:2])
        assert MusifySequence(models[:2]) != sequence

    def test_copy(self, sequence: MusifySequence, models: list[MusifyResource]):
        sequence_copy = sequence.copy()
        assert isinstance(sequence_copy, sequence.__class__)
        assert sequence_copy is not sequence
        assert sequence_copy.items is not sequence.items
        assert sequence_copy.items == sequence.items

    def test_getitem(self, sequence: MusifySequence, models: list[MusifyResource]):
        assert sequence[0] == models[0]
        assert sequence[:2] == models[:2]
        assert sequence[next(iter(models[0].unique_keys))] == models[0]

    def test_getitem_fails(self, sequence: MusifySequence, models: list[MusifyResource]):
        sequence = MusifySequence(models[2:])
        with pytest.raises(KeyError):
            assert sequence[next(iter(models[0].unique_keys))]
        with pytest.raises(KeyError):
            assert sequence["unknown"]

    @staticmethod
    def test_intersection(models: list[MusifyResource]):
        index = len(models) // 2
        models, other = tuple(models[index:]), tuple(models[:index])
        sequence = MusifySequence(models)

        assert sequence.intersection(models) == models
        assert sequence.intersection(other) == ()
        assert sequence.intersection(other + models[2:]) == models[2:]

    @staticmethod
    def test_difference(models: list[MusifyResource]):
        index = len(models) // 2
        models, other = tuple(models[index:]), tuple(models[:index])
        sequence = MusifySequence(models)

        assert sequence.difference(models) == ()
        assert sequence.difference(other) == models
        assert sequence.difference(other + models[2:]) == models[:2]

    @staticmethod
    def test_outer_difference(models: list[MusifyResource]):
        index = len(models) // 2
        models, other = tuple(models[index:]), tuple(models[:index])
        sequence = MusifySequence(models)

        assert sequence.outer_difference(models) == ()
        assert sequence.outer_difference(other) == other
        assert sequence.outer_difference(other + models[2:]) == other


class TestMusifyMutableSequence:
    def test_setitem(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models[:3])
        model = choice(models[3:])
        assert model not in sequence

        sequence[0] = model
        assert model in sequence
        assert sequence.items[0] == model
        assert all(key in sequence._items_mapped for key in model.unique_keys)

        sequence[0:2] = models[1:3]
        assert all(m in sequence for m in models[1:3])
        assert sequence.items[0:2] == models[1:3]
        assert all(key in sequence._items_mapped for m in models[1:3] for key in m.unique_keys)

    def test_setitem_fails(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models[:3])

        with pytest.raises(MusifyValueError):
            sequence[0] = "invalid value"

    def test_delitem_on_index(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models)
        model = models[0]
        assert model in sequence

        del sequence[sequence.items.index(model)]
        assert model not in sequence
        assert all(key not in sequence._items_mapped for key in model.unique_keys)

        del sequence[0:2]
        assert all(model not in sequence for model in models[1:3])
        assert all(key not in sequence._items_mapped for m in models[1:3] for key in m.unique_keys)

    def test_delitem_on_resource(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models)
        model = choice(models)
        assert model in sequence

        del sequence[model]
        assert model not in sequence
        assert all(key not in sequence for key in model.unique_keys)

    def test_mutable_dunder_methods(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models[:3])
        original = sequence.copy()
        assert sequence + sequence == sequence.items + sequence.items
        assert sequence - sequence == []
        assert sequence.items == original.items
        assert sequence._items_mapped == original._items_mapped

        sequence += models[3:]
        assert len(sequence) == len(original) + len(models[3:])
        assert sequence.items != original.items
        assert sequence._items_mapped != original._items_mapped
        assert all(key in sequence._items_mapped for m in models[3:] for key in m.unique_keys)

        sequence -= original
        assert len(sequence) == len(models[3:])
        assert sequence.items == models[3:]
        assert all(key in sequence._items_mapped for m in models[3:] for key in m.unique_keys)

    def test_append(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models[3:])
        original_length = len(sequence.items)
        model = models[0]
        assert model not in sequence

        sequence.append(model)
        assert len(sequence) == original_length + 1
        assert model in sequence
        assert sequence.items[-1] == model
        assert all(key in sequence._items_mapped for key in model.unique_keys)
        expected_keys = set(sequence._items_mapped)

        # adds duplicates
        sequence.append(model)
        assert len(sequence) == original_length + 2
        assert sequence.items[-1] == model
        assert sequence.items[-2] == model
        assert sequence._items_mapped.keys() == expected_keys

    def test_extend(self, models: list[MusifyResource]):
        sequence = MusifyMutableSequence(models[3:])
        original_length = len(sequence.items)
        models = models[:3]
        assert all(m not in sequence for m in models)

        sequence.extend(models)
        assert len(sequence) == original_length + len(models)
        assert all(m in sequence for m in models)
        assert sequence.items[-len(models):] == models
        assert all(key in sequence._items_mapped for m in models for key in m.unique_keys)
        expected_keys = set(sequence._items_mapped)

        # adds duplicates
        sequence.extend(models)
        assert len(sequence) == original_length + 2 * len(models)
        assert sequence.items[-len(models):] == models
        assert sequence.items[-len(models) * 2:-len(models)] == models
        assert sequence._items_mapped.keys() == expected_keys

    def test_insert(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models[3:])
        original_length = len(sequence.items)
        model = models[0]
        assert model not in sequence

        sequence.insert(2, model)
        assert len(sequence) == original_length + 1
        assert model in sequence
        assert sequence.items[2] == model
        assert all(key in sequence._items_mapped for key in model.unique_keys)
        expected_keys = set(sequence._items_mapped)

        # adds duplicates
        sequence.insert(2, model)
        assert len(sequence) == original_length + 2
        assert sequence.items[2] == model
        assert sequence.items[3] == model
        assert sequence._items_mapped.keys() == expected_keys

    def test_remove(self, models: list[MusifyResource]) -> None:
        sequence = MusifyMutableSequence(models[3:])

        # just check it calls delitem
        with mock.patch.object(sequence.__class__, "__delitem__") as mocked_delitem:
            sequence.remove(models[0])
            mocked_delitem.asssert_called_once_with(models[0])

    def test_clear(self, models: list[MusifyResource]):
        sequence = MusifyMutableSequence(models[3:])
        assert sequence.items
        assert sequence._items_mapped

        sequence.clear()
        assert not sequence.items
        assert not sequence._items_mapped
