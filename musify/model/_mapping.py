from collections.abc import Iterable, Mapping, MutableMapping, Hashable
from typing import Self, Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from musify.exception import MusifyKeyError, MusifyTypeError, MusifyValueError
from musify.model import MusifyResource


class MusifyMapping[KT, VT: MusifyResource](Mapping[KT | VT, VT]):
    """Stores :py:class:`MusifyResource` items mapped according to their unique keys."""
    # noinspection PyUnusedLocal
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        items_schema = core_schema.is_instance_schema(MusifyResource)
        schema = core_schema.union_schema([
            core_schema.is_instance_schema(cls),
            items_schema,
            core_schema.dict_schema(keys_schema=core_schema.any_schema(), values_schema=items_schema),
            core_schema.set_schema(items_schema=items_schema),
            core_schema.tuple_schema(items_schema=[items_schema], variadic_item_index=0),
            core_schema.list_schema(items_schema=items_schema),
        ])

        return core_schema.no_info_after_validator_function(
            function=cls._construct,
            schema=handler(schema),
            serialization=core_schema.plain_serializer_function_ser_schema(cls.items.fget)
        )

    @classmethod
    def _construct(cls, value: Self | Iterable[VT] | Mapping[Any, VT]) -> Self:
        if isinstance(value, cls):
            return value
        if isinstance(value, MusifyResource):
            return cls((value,))
        if isinstance(value, Mapping):
            return cls(value.values())
        if isinstance(value, Iterable):
            return cls(value)
        raise MusifyTypeError(f"Unrecognised value type: {value!r}")

    @property
    def items(self) -> Mapping[KT | VT, VT]:
        """The items in this collection"""
        return self._items

    def __init__(self, items: Iterable[VT] = None):
        if items is None:
            items = ()
        elif isinstance(items, Mapping):
            items = items.values()

        self._items: dict[KT | VT, VT] = {key: item for item in items for key in item.unique_keys}

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

        return not (self.keys() - other.keys())

    def __ne__(self, other: Self):
        return not self.__eq__(other)

    def __contains__(self, __item: KT | VT):
        if isinstance(__item, MusifyResource):
            return any(key in self._items for key in __item.unique_keys)
        if isinstance(__item, Hashable) and __item in self._items:
            return True
        return any(__item == i for i in self._items.values())

    def __getitem__(self, __key: KT | VT) -> VT:
        if isinstance(__key, MusifyResource):
            try:
                return next(self._items[key] for key in __key.unique_keys if key in self._items)
            except StopIteration:
                raise MusifyKeyError(
                    f"No items found for the model with keys: {", ".join(map(str, __key.unique_keys))}"
                )

        return self._items[__key]

    def copy(self) -> Self:
        """Return a shallow copy of this mapping"""
        return self.__class__(self._items.copy())


class MusifyMutableMapping[KT, VT: MusifyResource](MusifyMapping[KT, VT], MutableMapping[KT | VT, VT]):
    """Stores :py:class:`MusifyResource` items mapped according to their unique keys."""
    def __setitem__(self, __key: KT | VT, __value: VT):
        """Replace the item at a given ``__key`` with the given ``__value``."""
        if not isinstance(__value, MusifyResource):
            raise MusifyValueError("Value given must be a valid musify resource.")

        for key in __value.unique_keys:
            self._items[key] = __value

    def __delitem__(self, __key: KT | VT):
        if isinstance(__key, MusifyResource):
            if not any(key in self._items for key in __key.unique_keys):
                raise MusifyKeyError(
                    f"No items found for the model with keys: {", ".join(map(str, __key.unique_keys))}"
                )
            for key in __key.unique_keys:
                if key in self._items:
                    del self._items[key]
            return

        del self._items[__key]

    def add(self, __item: VT) -> None:
        """Add an item to this mapping"""
        if not isinstance(__item, MusifyResource):
            raise MusifyValueError("Item given must be a valid musify resource.")
        for key in __item.unique_keys:
            self._items[key] = __item

    def update(self, __m: Iterable[VT] | Mapping[KT | VT], **kwargs) -> None:
        """Merge this mapping with another mapping or iterable of items"""
        if isinstance(__m, Mapping):
            __m = __m.values()

        __items_iter = ((key, item) for item in __m for key in item.unique_keys)
        self._items.update(dict(__items_iter))

    def remove(self, __item: KT | VT) -> None:
        """Remove one item from this mapping"""
        del self[__item]
