from abc import abstractmethod
from collections.abc import Mapping, Hashable
from typing import Collection, Sequence, MutableSequence, Iterable, overload, SupportsIndex, Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from musify.exception import MusifyValueError
from musify.model import MusifyResource, MusifyMapping, MusifyMutableMapping


class MusifySequence[TK, TV: MusifyResource](Sequence[TV]):
    """
    Stores :py:class:`MusifyResource` items with optimisations
    to execute functionality on the sequence according to the item's unique keys.
    """
    # noinspection PyUnusedLocal
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        items_schema = core_schema.is_instance_schema(MusifyResource)
        schema = core_schema.union_schema([
            core_schema.is_instance_schema(cls),
            items_schema,
            core_schema.generator_schema(items_schema=items_schema),
        ])

        return core_schema.no_info_after_validator_function(
            function=cls._validate,
            schema=handler(schema),
            serialization=core_schema.plain_serializer_function_ser_schema(cls.items.fget)
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
    def items(self) -> list[TV]:
        """The items in this sequence"""
        return self._items

    def __init__(self, items: Iterable[TV] | Mapping[Any, TV] = None):
        if items is None:
            items = ()
        elif isinstance(items, Mapping):
            items = items.values()

        self._items: list[TV] = list(items)
        self._items_mapped: MusifyMutableMapping[TK, TV] = MusifyMutableMapping(self._items)

    def __repr__(self):
        return repr(self.items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __eq__(self, other: Self):
        """Matching type and all keys in this mapping present in the other mapping"""
        if self is other:
            return True
        elif not isinstance(other, self.__class__):
            return False

        return self.items == other.items

    def __ne__(self, other: Self):
        return not self.__eq__(other)

    def __contains__(self, __item: TK | TV):
        if isinstance(__item, MusifyResource):
            return __item in self._items_mapped
        return __item in self._items_mapped

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> TV: ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> list[TV]: ...

    def __getitem__(self, index) -> TV | list[TV]:
        if isinstance(index, int | slice):
            try:
                return self._items[index]
            except IndexError:
                pass
        return self._items_mapped[index]

    def copy(self) -> Self:
        """Return a shallow copy of this sequence"""
        return self.__class__(self._items.copy())

    def intersection(self, other: Collection[TV]) -> tuple[TV, ...]:
        """
        Return the intersection between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in both this collection and the ``other`` collection).
        """
        def _match(item: MusifyResource) -> bool:
            if not isinstance(other, MusifySequence):
                return item in other
            return any(key in other._items_mapped for key in item.unique_keys)

        return tuple(filter(_match, self._items))

    def difference(self, other: Collection[TV]) -> tuple[TV, ...]:
        """
        Return the difference between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in this collection but not the ``other`` collection).
        """
        def _match(item: MusifyResource) -> bool:
            if not isinstance(other, MusifySequence):
                return item not in other
            return all(key not in other._items_mapped for key in item.unique_keys)

        return tuple(filter(_match, self._items))

    def outer_difference(self, other: Iterable[TV]) -> tuple[TV, ...]:
        """
        Return the outer difference between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in the ``other`` collection but not in this collection).
        """
        def _match(item: MusifyResource) -> bool:
            if not isinstance(other, MusifySequence):
                return item not in self._items
            return all(key not in self._items_mapped for key in item.unique_keys)

        return tuple(filter(_match, other))


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

    def __setitem__(self, index: SupportsIndex, value: TV | Iterable[TV]):
        if not isinstance(value, slice | Iterable | MusifyResource) or isinstance(value, str):
            raise MusifyValueError(f"Invalid value: {value}")

        self._items[index] = value
        if isinstance(value, MusifyResource):
            self._items_mapped.add(value)
        else:
            self._items_mapped.update(value)

    def __delitem__(self, index: SupportsIndex | TV) -> None:
        if isinstance(index, MusifyResource):
            self._items_mapped.remove(index)
            self._items.remove(index)
            return

        if isinstance(item := self._items[index], MusifyResource):
            del self._items_mapped[item]
        else:
            for it in item:
                del self._items_mapped[it]

        del self._items[index]

    def __add__(self, other: Iterable[TV]):
        items = self._items.copy()
        items.extend(other)
        return items

    def __iadd__(self, other: Iterable[TV]):
        self.extend(other)
        return self

    def __sub__(self, other: Iterable[TV]):
        items = self._items.copy()
        for item in other:
            items.remove(item)
        return items

    def __isub__(self, other: Iterable[TV]):
        for item in other:
            self.remove(item)
        return self

    def append(self, __object: TV) -> None:
        """Add an item to the end of this sequence"""
        self._items.append(__object)
        self._items_mapped.add(__object)

    def extend(self, __iterable: Iterable[TV], allow_duplicates: bool = True) -> None:
        """Add many items to the end of this sequence"""
        if isinstance(__iterable, MusifySequence):
            __iterable = __iterable.items
        elif not isinstance(__iterable, Collection):
            __iterable = tuple(__iterable)

        __items_iter = dict((key, item) for item in __iterable for key in item.unique_keys)
        if not allow_duplicates:
            __items_iter = dict((key, item) for key, item in __items_iter.items() if key not in self._items)
            __iterable = (item for item in __iterable if any(key in self._items for key in item.unique_keys))

        self._items.extend(__iterable)
        self._items_mapped.update(dict(__items_iter))

    def insert(self, __index: int, __object: TV, allow_duplicates: bool = True) -> None:
        """Insert the item at the given index"""
        if not allow_duplicates and __object in self._items_mapped:
            return

        self._items.insert(__index, __object)
        self._items_mapped.add(__object)

    def remove(self, __value: TV) -> None:
        """Remove one item from this sequence"""
        del self[__value]

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
