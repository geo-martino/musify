"""
The fundamental core collection classes for the entire package.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import MutableSequence, Iterable, Mapping, Collection
from typing import Any, SupportsIndex, Self

from musify.processors.sort import ShuffleMode, ShuffleBy, ItemSorter
from musify.shared.core.base import Nameable, NameableTaggableMixin, AttributePrinter, Item
from musify.shared.core.enum import Field
from musify.shared.exception import MusifyTypeError, MusifyKeyError
from musify.shared.types import UnitSequence


class ItemCollection[T: Item](AttributePrinter, NameableTaggableMixin, MutableSequence[T], metaclass=ABCMeta):
    """Generic class for storing a collection of items."""

    @property
    @abstractmethod
    def items(self) -> list[T]:
        """The items in this collection"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        """
        Validate the given :py:class:`Item` by ensuring it matches the allowed item type for this collection.
        Used to validate input :py:class:`Item` types given to functions that
        modify the stored items in this collection.

        :param items: The item or items to validate
        :return: True if valid, False if not.
        """
        raise NotImplementedError

    def count(self, __item: T) -> int:
        """Return the number of occurrences of the given :py:class:`Item` in this collection"""
        if not self._validate_item_type(__item):
            raise MusifyTypeError(type(__item).__name__)
        return self.items.count(__item)

    def index(self, __item: T, __start: SupportsIndex = None, __stop: SupportsIndex = None) -> int:
        """
        Return first index of item from items in this collection.

        :raise ValueError: If the value is not present.
        :raise MusifyTypeError: If given item does not match the item type of this collection.
        """
        if not self._validate_item_type(__item):
            raise MusifyTypeError(type(__item).__name__)
        return self.items.index(__item, __start or 0, __stop or len(self.items))

    def copy(self) -> list[T]:
        """Return a shallow copy of the list of items in this collection"""
        return [item for item in self.items]

    def append(self, __item: T, allow_duplicates: bool = True) -> None:
        """Append one item to the items in this collection"""
        if not self._validate_item_type(__item):
            raise MusifyTypeError(type(__item).__name__)
        if allow_duplicates or __item not in self.items:
            self.items.append(__item)

    def extend(self, __items: Iterable[T], allow_duplicates: bool = True) -> None:
        """Append many items to the items in this collection"""
        if not self._validate_item_type(__items):
            raise MusifyTypeError([type(i).__name__ for i in __items])
        if isinstance(__items, ItemCollection):
            __items = __items.items

        if allow_duplicates:
            self.items.extend(__items)
        else:
            self.items.extend(item for item in __items if item not in self.items)

    def insert(self, __index: int, __item: T, allow_duplicates: bool = True) -> None:
        """Insert given :py:class:`Item` before the given index"""
        if not self._validate_item_type(__item):
            raise MusifyTypeError(type(__item))
        if allow_duplicates or __item not in self.items:
            self.items.insert(__index, __item)

    def remove(self, __item: T) -> None:
        """Remove one item from the items in this collection"""
        if not self._validate_item_type(__item):
            raise MusifyTypeError(type(__item))
        self.items.remove(__item)

    def pop(self, __item: SupportsIndex = None) -> T:
        """Remove one item from the items in this collection and return it"""
        return self.items.pop(__item) if __item else self.items.pop()

    def reverse(self) -> None:
        """Reverse the order of items in this collection in-place"""
        self.items.reverse()

    def clear(self) -> None:
        """Remove all items from this collection"""
        self.items.clear()

    def sort(
            self,
            fields: UnitSequence[Field | None] | Mapping[Field | None, bool] = (),
            shuffle_mode: ShuffleMode = ShuffleMode.NONE,
            shuffle_by: ShuffleBy = ShuffleBy.TRACK,
            shuffle_weight: float = 1.0,
            key: Field | None = None,
            reverse: bool = False,
    ) -> None:
        """
        Sort items in this collection in-place based on given conditions.
        If key is given,

        :param fields:
            * When None and ShuffleMode is RANDOM, shuffle the tracks. Otherwise, do nothing.
            * List of tags/properties to sort by.
            * Map of `{<tag/property>: <reversed>}`. If reversed is true, sort the ``tag/property`` in reverse.
        :param shuffle_mode: The mode to use for shuffling.
        :param shuffle_by: The field to shuffle by when shuffling.
        :param shuffle_weight: The weights (between 0 and 1) to apply to shuffling modes that can use it.
            This value will automatically be limited to within the accepted range 0 and 1.
        :param key: Tag or property to sort on. Can be given instead of ``fields`` for a simple sort.
            If set, all other fields apart from ``reverse`` are ignored.
            If None, ``fields``, ``shuffle_mode``, ``shuffle_by``, and ``shuffle_weight`` are used to apply sorting.
        :param reverse: If true, reverse the order of the sort at the end.
        """
        if key is not None:
            ItemSorter.sort_by_field(self.items, field=key)
        else:
            ItemSorter(
                fields=fields, shuffle_mode=shuffle_mode, shuffle_by=shuffle_by, shuffle_weight=shuffle_weight
            )(self.items)

        if reverse:
            self.items.reverse()

    @staticmethod
    def _condense_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        """Condense the attributes of the given map for cleaner attribute displaying"""
        def condense(key: str, value: Any) -> tuple[str, Any]:
            """Decide whether this key-value pair should be condensed and condense them."""
            if isinstance(value, Collection) and not isinstance(value, str):
                if any(isinstance(v, Nameable) for v in value) or len(value) > 20 or len(value) == 0:
                    return f"{key.rstrip("s")}_count", len(value)
            return key, value

        return dict(condense(k, v) for k, v in attributes.items())

    def as_dict(self):
        return self._condense_attributes(self._get_attributes())

    def json(self):
        return self._to_json(self._get_attributes())

    def __eq__(self, __collection: ItemCollection | Iterable[T]):
        """Names equal and all items equal in order"""
        name = self.name == __collection.name if isinstance(__collection, ItemCollection) else True
        length = len(self) == len(__collection)
        items = all(x == y for x, y in zip(self, __collection))
        return name and length and items

    def __ne__(self, __collection: ItemCollection | Iterable[T]):
        return not self.__eq__(__collection)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __reversed__(self):
        return reversed(self.items)

    def __contains__(self, __item: T):
        return any(__item == i for i in self.items)

    def __add__(self, __items: list[T] | Self):
        if isinstance(__items, ItemCollection):
            return self.items + __items.items
        return self.items + __items

    def __iadd__(self, __items: Iterable[T]):
        self.extend(__items)
        return self

    def __sub__(self, __items: Iterable[T]):
        items = self.copy()
        for item in __items:
            items.remove(item)
        return items

    def __isub__(self, __items: Iterable[T]):
        for item in __items:
            self.remove(item)
        return self

    @abstractmethod
    def __getitem__(self, __key: str | int | slice | Item) -> T | list[T] | list[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI.
        If an item is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        """
        raise NotImplementedError

    def __setitem__(self, __key: str | int | T, __value: T):
        """Replace the item at a given ``__key`` with the given ``__value``."""
        try:
            item = self[__key]
        except KeyError:
            raise MusifyKeyError(f"Given index is out of range: {__key}")

        if type(__value) is not type(item):  # only merge attributes if matching types
            raise MusifyTypeError("Trying to set on mismatched item types")

        self.items[self.index(item)] = __value

    def __delitem__(self, __key: str | int | T):
        self.remove(__key)
