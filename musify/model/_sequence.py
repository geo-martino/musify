from abc import abstractmethod
from collections.abc import Mapping, Iterable, Sequence, MutableSequence, Set, Iterator
from typing import Any, Self, overload, get_args

from pydantic import GetCoreSchemaHandler, validate_call, ConfigDict
from pydantic_core import core_schema

from musify.exception import MusifyValueError
from musify.model import MusifyResource, MusifyMutableMapping


class MusifySequence[TK, TV: MusifyResource](Sequence[TV]):
    """
    Stores :py:class:`MusifyResource` items with optimisations
    to execute functionality on the sequence according to the item's unique keys.
    """
    # noinspection PyUnusedLocal
    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        args = get_args(source)
        if args:
            keys_schema = handler.generate_schema(args[0])
            values_schema = handler.generate_schema(args[1])
        else:
            keys_schema = core_schema.any_schema()
            values_schema = core_schema.is_instance_schema(MusifyResource)

        schema = core_schema.union_schema([
            core_schema.is_instance_schema(cls),
            values_schema,
            core_schema.dict_schema(keys_schema=keys_schema, values_schema=values_schema),
            core_schema.set_schema(values_schema),
            core_schema.tuple_variable_schema(values_schema),
            core_schema.list_schema(values_schema),
        ])

        return core_schema.no_info_after_validator_function(
            function=cls._validate,
            schema=handler(schema),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: x._items)
        )

    @classmethod
    def _validate(cls, value: str | dict[str, Any]) -> Self:
        if isinstance(value, cls):
            return value
        if isinstance(value, MusifyResource):
            return cls((value,))
        if isinstance(value, Iterable):
            return cls(value)
        raise MusifyValueError(f"Invalid value: {value}")

    @property
    def unique(self) -> Iterator[TV]:
        """The unique items in this sequence"""
        seen = set()
        for key, value in self._items_mapped.items():
            if key in seen:
                continue

            yield value
            seen.add(key)

    def __init__(self, items: Iterable[TV] | Mapping[Any, TV] = None):
        if items is None:
            items = ()
        elif isinstance(items, Mapping):
            items = items.values()

        self._items: list[TV] = list(items)
        self._items_mapped: MusifyMutableMapping[TK, TV] = MusifyMutableMapping(self._items)

    def __repr__(self):
        return repr(self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __eq__(self, other: Self):
        """Matching type and all keys in this mapping present in the other mapping"""
        if self is other:
            return True
        elif not isinstance(other, self.__class__):
            return super().__eq__(other)

        return self._items == other._items

    def __ne__(self, other: Self):
        return not self.__eq__(other)

    @validate_call
    def __contains__(self, __item: TK | TV | Iterable[TK | TV]) -> bool:
        return __item in self._items_mapped

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> TV: ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> list[TV]: ...

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def __getitem__(self, index: int | slice | TK | TV) -> TV | list[TV]:
        if isinstance(index, int | slice):
            try:
                return self._items[index]
            except IndexError:
                pass
        return self._items_mapped[index]

    def copy(self) -> Self:
        """Return a shallow copy of this sequence"""
        return self.__class__(self._items.copy())

    @validate_call
    def intersection(self, other: Sequence[TV] | Set[TV]) -> tuple[TV, ...]:
        """
        Return the intersection between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in both this collection and the ``other`` collection).
        """
        return tuple(item for item in self._items if item in other)

    @validate_call
    def difference(self, other: Sequence[TV] | Set[TV]) -> tuple[TV, ...]:
        """
        Return the difference between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in this collection but not the ``other`` collection).
        """
        return tuple(item for item in self._items if item not in other)

    @validate_call
    def outer_difference(self, other: Sequence[TV] | Set[TV]) -> tuple[TV, ...]:
        """
        Return the outer difference between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in the ``other`` collection but not in this collection).
        """
        return tuple(item for item in other if item not in self)


class MusifyMutableSequence[TK, TV: MusifyResource](MusifySequence[TK, TV], MutableSequence[TV]):
    """
    Stores :py:class:`MusifyResource` items with optimisations
    to execute functionality on the sequence according to the item's unique keys.
    """
    @overload
    @abstractmethod
    def __setitem__(self, index: int, value: TV) -> None: ...

    @overload
    @abstractmethod
    def __setitem__(self, index: slice, value: Iterable[TV]) -> None: ...

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def __setitem__(self, index: int | slice, value: TV | Iterable[TV]):
        self._items[index] = value
        if isinstance(value, MusifyResource):
            self._items_mapped.add(value)
        else:
            self._items_mapped.update(value)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def __delitem__(self, index: int | slice) -> None:
        if isinstance(item := self[index], MusifyResource):  # index is an int
            self.remove(item)
            return

        for it in item:  # index is a slice
            self.remove(it)

    @validate_call
    def __add__(self, other: Iterable[TV]):
        items = self._items.copy()
        items.extend(other)
        return items

    @validate_call
    def __iadd__(self, other: Iterable[TV]):
        self.extend(other)
        return self

    @validate_call
    def __sub__(self, other: Iterable[TV]):
        items = self._items.copy()
        for item in other:
            items.remove(item)
        return items

    @validate_call
    def __isub__(self, other: Iterable[TV]):
        for item in other:
            self.remove(item)
        return self

    @validate_call
    def __or__(self, other: Sequence[TV]) -> Self:
        items = self.copy()
        return items.merge(other)

    @validate_call
    def __ior__(self, other: Sequence[TV]) -> Self:
        self.merge(other)
        return self

    @validate_call
    def append(self, __object: TV, allow_duplicates: bool = True) -> None:
        """Add an item to the end of this sequence"""
        if not allow_duplicates and __object in self._items_mapped:
            return

        self._items.append(__object)
        self._items_mapped.add(__object)

    @validate_call
    def extend(self, __iterable: Iterable[TV], allow_duplicates: bool = True) -> None:
        """Add many items to the end of this sequence"""
        if not allow_duplicates:
            __iterable = (item for item in __iterable if item not in self._items_mapped)

        items = list(__iterable)
        self._items.extend(items)
        self._items_mapped.update(items)

    @validate_call
    def insert(self, __index: int, __object: TV, allow_duplicates: bool = True) -> None:
        """Insert the item at the given index"""
        if not allow_duplicates and __object in self._items_mapped:
            return

        self._items.insert(__index, __object)
        self._items_mapped.add(__object)

    @validate_call
    def merge(self, other: Sequence[TV], reference: Sequence[TV] | None = None) -> None:
        """
        Merge this sequence with another collection.

        By providing just a collection of items, this function will add all new items (without duplicates)
        to the end of this sequence.

        Optionally, a 3-way sync may be achieved by providing a ``reference`` sequence to compare the current sequence
        and the ``other`` sequence to. Items present in both this sequence and the ``reference``
        but not in the ``other`` sequence will be removed from this sequence.

        :param other: The sequence of items to merge with.
        :param reference: The reference sequence to compare this sequence and the ``other`` sequence to.
        """
        if reference is None:
            self.extend(other, allow_duplicates=False)
            return

        for item in reference:
            if item not in other and item in self:
                self.remove(item)

        # noinspection PyTypeChecker
        self.extend(MusifySequence.outer_difference(reference, other), allow_duplicates=False)

    @validate_call
    def remove(self, __value: TV) -> None:
        """Remove one item from this sequence"""
        self._items.remove(__value)
        del self._items_mapped[__value]

    def clear(self) -> None:
        """Remove all items from this sequence"""
        self._items.clear()
        self._items_mapped.clear()

    # TODO: figure this out
    # def sort(
    #         self,
    #         fields: UnitSequence[Field | None] | Mapping[Field | None, bool] = (),
    #         shuffle_mode: ShuffleMode | None = None,
    #         shuffle_weight: float = 1.0,
    #         key: Field | None = None,
    #         reverse: bool = False,
    # ) -> None:
    #     """
    #     Sort items in this collection in-place based on given conditions.
    #     If key is given,
    #
    #     :param fields:
    #         * When None and ShuffleMode is RANDOM, shuffle the tracks. Otherwise, do nothing.
    #         * List of tags/properties to sort by.
    #         * Map of `{<tag/property>: <reversed>}`. If reversed is true, sort the ``tag/property`` in reverse.
    #     :param shuffle_mode: The mode to use for shuffling.
    #     :param shuffle_weight: The weights (between 0 and 1) to apply to shuffling modes that can use it.
    #         This value will automatically be limited to within the accepted range 0 and 1.
    #     :param key: Tag or property to sort on. Can be given instead of ``fields`` for a simple sort.
    #         If set, all other fields apart from ``reverse`` are ignored.
    #         If None, ``fields``, ``shuffle_mode``, ``shuffle_by``, and ``shuffle_weight`` are used to apply sorting.
    #     :param reverse: If true, reverse the order of the sort at the end.
    #     """
    #     if key is not None:
    #         ItemSorter.sort_by_field(self._items, field=key)
    #     else:
    #         ItemSorter(fields=fields, shuffle_mode=shuffle_mode, shuffle_weight=shuffle_weight)(self._items)
    #
    #     if reverse:
    #         self._items.reverse()