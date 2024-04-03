"""
Processor that sorts the given collection of items based on given configuration.
"""
from collections.abc import Callable, Mapping, MutableMapping, Sequence, MutableSequence, Iterable
from copy import copy
from datetime import datetime
from random import shuffle
from typing import Any

from musify.core.base import MusifyItem
from musify.core.enum import MusifyEnum, Field
from musify.processors.base import Processor
from musify.types import UnitSequence, UnitIterable
from musify.utils import flatten_nested, strip_ignore_words, to_collection, limit_value


class ShuffleMode(MusifyEnum):
    """Represents the possible shuffle modes to use when shuffling items using :py:class:`ItemSorter`."""
    RANDOM = 0
    HIGHER_RATING = 1
    RECENT_ADDED = 2
    DIFFERENT_ARTIST = 3


class ItemSorter(Processor):
    """
    Sort items in-place based on given conditions.

    :param fields: Fields to sort by. If defined, this value will always take priority over any shuffle settings
        i.e. shuffle settings will be ignored.
        * List of tags/properties to sort by.
        * Map of ``{<tag/property>: <reversed>}``. If reversed is true, sort the ``tag/property`` in reverse.
    :param shuffle_mode: The mode to use for shuffling. Only used when no ``fields`` are given.
        WARNING: Currently only ``RANDOM`` shuffle mode has been implemented.
        Any other given value will default to ``RANDOM`` shuffling.
    :param shuffle_weight: The weights (between -1 and 1) to apply to certain shuffling modes.
        This value will automatically be limited to within the valid range -1 and 1.
        Only used when no ``fields`` are given and shuffle_mode is not None or ``RANDOM``.
    """

    __slots__ = ("sort_fields", "shuffle_mode", "shuffle_weight")

    @classmethod
    def sort_by_field(cls, items: list[MusifyItem], field: Field | None = None, reverse: bool = False) -> None:
        """
        Sort items by the values of a given field.

        :param items: List of items to sort
        :param field: Tag or property to sort on. If None and reverse is True, reverse the order of the list.
        :param reverse: If true, reverse the order of the sort.
        """
        if field is None:
            if reverse:
                items.reverse()
            return

        tag_name = field.map(field)[0].name.lower()

        # attempt to find an example value to determine the value type for this sort
        example_value = None
        for item in items:
            example_value = item[tag_name]
            if example_value is not None:
                break
        if example_value is None:
            # if no example value found, all values are None and so no sort can happen safely. Skip
            return

        # get sort key based on value type
        if isinstance(example_value, datetime):  # key converts datetime to floats
            def sort_key(t: MusifyItem) -> float:
                """Get the sort key for timestamp tags from the given ``t``"""
                value = t[tag_name]
                return value.timestamp() if value is not None else 0.0
        elif isinstance(example_value, str):  # key strips ignore words from string
            sort_key: Callable[[MusifyItem], (bool, str)] = lambda t: strip_ignore_words(t[tag_name])
        else:
            sort_key: Callable[[MusifyItem], object] = lambda t: t[tag_name] if t[tag_name] else 0

        items.sort(key=sort_key, reverse=reverse)

    @classmethod
    def group_by_field[T: MusifyItem](cls, items: UnitIterable[T], field: Field | None = None) -> dict[Any, list[T]]:
        """
        Group items by the values of a given field.

        :param items: List of items to sort.
        :param field: Tag or property to group by. None returns map of ``{None: <items>}``.
        :return: Map of grouped items.
        """
        if field is None:  # group by None
            return {None: to_collection(items, list)}

        tag_name = field.map(field)[0].name.lower()

        def group(v: Any) -> None:
            """Group items by the given value ``v``"""
            if grouped.get(v) is None:
                grouped[v] = []
            grouped[v].append(item)

        grouped: dict[Any | None, list[T]] = {}
        for item in items:  # produce map of grouped values
            value = to_collection(item[tag_name])
            if isinstance(value, Iterable):
                for val in value:
                    group(val)
            else:
                group(value)

        return grouped

    def __init__(
            self,
            fields: UnitSequence[Field | None] | Mapping[Field | None, bool] = (),
            shuffle_mode: ShuffleMode | None = None,
            shuffle_weight: float = 0.0
    ):
        super().__init__()
        fields = to_collection(fields, list) if isinstance(fields, Field) else fields
        self.sort_fields: Mapping[Field | None, bool] = {field: False for field in fields} \
            if isinstance(fields, Sequence) else fields

        self.shuffle_mode = shuffle_mode
        self.shuffle_weight = limit_value(shuffle_weight, floor=-1, ceil=1)

    def __call__(self, *args, **kwargs) -> None:
        return self.sort(*args, **kwargs)

    def sort(self, items: MutableSequence[MusifyItem]) -> None:
        """Sorts a list of ``items`` in-place."""
        if len(items) == 0:
            return

        if self.sort_fields:
            items_nested = self._sort_by_fields({None: items}, fields=self.sort_fields)
            items.clear()
            items.extend(flatten_nested(items_nested))
        elif self.shuffle_mode == ShuffleMode.RANDOM:  # random
            shuffle(items)
        elif self.shuffle_mode == ShuffleMode.HIGHER_RATING:
            shuffle(items)  # TODO: implement this shuffle mode correctly
        elif self.shuffle_mode == ShuffleMode.RECENT_ADDED:
            shuffle(items)  # TODO: implement this shuffle mode correctly
        elif self.shuffle_mode == ShuffleMode.DIFFERENT_ARTIST:
            shuffle(items)  # TODO: implement this shuffle mode correctly

    @classmethod
    def _sort_by_fields(cls, items_grouped: MutableMapping, fields: MutableMapping[Field, bool]) -> MutableMapping:
        """
        Sort items by the given fields recursively in the order given.

        :param items_grouped: Map of items grouped by the last sort value.
        :param fields: Map of ``{<tag/property>: <reversed>}``.
            If reversed is True, sort the ``tag/property`` in reverse.
        :return: Map of grouped and sorted items.
        """
        field, reverse = next(iter(fields.items()), (None, None))
        if field is None:  # sorting complete
            return items_grouped

        fields = copy(fields)
        fields.pop(field)

        # sort each group and recurse through each field for each group
        for i, (key, items) in enumerate(items_grouped.items(), 1):
            cls.sort_by_field(items=items, field=field, reverse=reverse)
            items_grouped[key] = cls._sort_by_fields(cls.group_by_field(items, field=field), fields=fields)

        return items_grouped

    def as_dict(self):
        fields = None
        if isinstance(self.sort_fields, Mapping):
            fields = {field.name: "desc" if r else "asc" for field, r in self.sort_fields.items()}

        return {
            "sort_fields": fields,
            "shuffle_mode": self.shuffle_mode,
            "shuffle_weight": self.shuffle_weight
        }
