"""
The fundamental core collection classes for the entire package.
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod, ABC
from collections.abc import MutableSequence, Iterable, Mapping, Collection
from dataclasses import dataclass
from typing import Any, SupportsIndex, Self

from musify.core.base import MusifyObject, MusifyItem
from musify.core.enum import Field
from musify.exception import MusifyTypeError, MusifyKeyError, MusifyAttributeError
from musify.file.base import File
from musify.libraries.remote.core import RemoteResponse
from musify.libraries.remote.core.base import RemoteObject
from musify.libraries.remote.core.processors.wrangle import RemoteDataWrangler
from musify.processors.sort import ShuffleMode, ItemSorter
from musify.types import UnitSequence


@dataclass
class ItemGetterStrategy(ABC):
    """Abstract base class for strategies relating to __getitem__ operations on a :py:class:`MusifyCollection`"""

    key: str

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the name to assign to this ItemGetter when logging"""
        raise NotImplementedError

    @abstractmethod
    def get_value_from_item(self, item: MusifyItem) -> str:
        """Retrieve the appropriate value from a given ``item`` for this ItemGetter type"""
        raise NotImplementedError

    def get_item[T](self, collection: MusifyCollection[T]) -> T:
        """Run this strategy and return the matched item from the given ``collection``"""
        try:
            return next(item for item in collection.items if str(self.get_value_from_item(item)) == self.key)
        except AttributeError:
            raise MusifyAttributeError(f"Items in collection do not have the attribute '{self.name}'")
        except StopIteration:
            raise MusifyKeyError(f"No matching item found for {self.name}: {self.key}")


class NameGetter(ItemGetterStrategy):
    """Get an item via its name for a :py:class:`MusifyCollection`"""
    def name(self) -> str:
        return "name"

    def get_value_from_item(self, item: MusifyObject) -> str:
        return item.name


class PathGetter(ItemGetterStrategy):
    """Get an item via its path for a :py:class:`MusifyCollection`"""
    def name(self) -> str:
        return "path"

    def get_value_from_item(self, item: File) -> str:
        return item.path


class RemoteIDGetter(ItemGetterStrategy):
    """Get an item via its remote ID for a :py:class:`MusifyCollection`"""
    def name(self) -> str:
        return "remote ID"

    def get_value_from_item(self, item: RemoteResponse) -> str:
        return item.id


class RemoteURIGetter(ItemGetterStrategy):
    """Get an item via its remote URI for a :py:class:`MusifyCollection`"""
    def name(self) -> str:
        return "URI"

    def get_value_from_item(self, item: MusifyItem | RemoteResponse) -> str:
        return item.uri


class RemoteURLAPIGetter(ItemGetterStrategy):
    """Get an item via its remote API URL for a :py:class:`MusifyCollection`"""
    def name(self) -> str:
        return "API URL"

    def get_value_from_item(self, item: RemoteObject) -> str:
        return item.url


class RemoteURLEXTGetter(ItemGetterStrategy):
    """Get an item via its remote external URL for a :py:class:`MusifyCollection`"""
    def name(self) -> str:
        return "external URL"

    def get_value_from_item(self, item: RemoteObject) -> str:
        return item.url_ext


class MusifyCollection[T: MusifyItem](MusifyObject, MutableSequence[T], metaclass=ABCMeta):
    """Generic class for storing a collection of musify items."""

    @property
    @abstractmethod
    def items(self) -> list[T]:
        """The items in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all items in this collection in seconds"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        """
        Validate the given :py:class:`MusifyItem` by ensuring it matches the allowed item type for this collection.
        Used to validate input :py:class:`MusifyItem` types given to functions that
        modify the stored items in this collection.

        :param items: The item or items to validate
        :return: True if valid, False if not.
        """
        raise NotImplementedError

    def __init__(self, remote_wrangler: RemoteDataWrangler | None = None):
        super().__init__()
        #: A :py:class:`RemoteDataWrangler` object for processing remote data
        self.remote_wrangler = remote_wrangler

    def count(self, __item: T) -> int:
        """Return the number of occurrences of the given :py:class:`MusifyItem` in this collection"""
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
        if isinstance(__items, MusifyCollection):
            __items = __items.items

        if allow_duplicates:
            self.items.extend(__items)
        else:
            self.items.extend(item for item in __items if item not in self.items)

    def insert(self, __index: int, __item: T, allow_duplicates: bool = True) -> None:
        """Insert given :py:class:`MusifyItem` before the given index"""
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
            shuffle_mode: ShuffleMode | None = None,
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
            ItemSorter(fields=fields, shuffle_mode=shuffle_mode, shuffle_weight=shuffle_weight)(self.items)

        if reverse:
            self.items.reverse()

    def difference(self, other: Iterable[T]) -> list[T]:
        """
        Return the difference between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in this collection but not the ``other`` collection).
        """
        return [item for item in other if item not in self]

    def intersection(self, other: Iterable[T]) -> list[T]:
        """
        Return the difference between the items in this collection and an ``other`` collection as a new list.

        (i.e. all items that are in both this collection and the ``other`` collection).
        """
        return [item for item in other if item in self]

    @staticmethod
    def _condense_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        """Condense the attributes of the given map for cleaner attribute displaying"""
        def condense(key: str, value: Any) -> tuple[str, Any]:
            """Decide whether this key-value pair should be condensed and condense them."""
            if isinstance(value, Collection) and not isinstance(value, str):
                if any(isinstance(v, MusifyObject) for v in value) or len(value) > 20 or len(value) == 0:
                    return f"{key.rstrip("s")}_count", len(value)
            return key, value

        return dict(condense(k, v) for k, v in attributes.items())

    def as_dict(self):
        return self._condense_attributes(self._get_attributes())

    def _json_attributes(self):
        return self._get_attributes()

    def __eq__(self, __collection: MusifyCollection | Iterable[T]):
        """Names equal and all items equal in order"""
        name = self.name == __collection.name if isinstance(__collection, MusifyCollection) else True
        length = len(self) == len(__collection)
        items = all(x == y for x, y in zip(self, __collection))
        return name and length and items

    def __ne__(self, __collection: MusifyCollection | Iterable[T]):
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
        if isinstance(__items, MusifyCollection):
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

    def __getitem__(
            self, __key: str | int | slice | MusifyItem | File | RemoteResponse
    ) -> T | list[T] | list[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI/ID/URL.
        If an :py:class:`MusifyItem` is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        If a :py:class:`RemoteObject` is given, the ID is extracted from this object
        and the matching RemoteObject from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]

        getters = self.__get_item_getters(__key)
        if not getters:
            raise MusifyKeyError(f"Unrecognised key type | {__key=} | type={type(__key).__name__}")

        caught_exceptions = []
        for getter in getters:
            try:
                return getter.get_item(self)
            except (MusifyAttributeError, MusifyKeyError) as ex:
                caught_exceptions.append(ex)

        raise MusifyKeyError(
            f"Key is invalid. The following errors were thrown: {[str(ex) for ex in caught_exceptions]}"
        )

    def __get_item_getters(self, __key: str | MusifyItem | File | RemoteResponse) -> list[ItemGetterStrategy]:
        getters = []
        if isinstance(__key, File):
            getters.append(PathGetter(__key.path))
        if isinstance(__key, RemoteResponse) and self.remote_wrangler:
            getters.append(RemoteIDGetter(__key.id))
        if isinstance(__key, MusifyItem) and __key.has_uri:
            getters.append(RemoteURIGetter(__key.uri))
        if isinstance(__key, MusifyObject):
            getters.append(NameGetter(__key.name))
        if isinstance(__key, str):
            getters.extend([
                RemoteIDGetter(__key),
                RemoteURIGetter(__key),
                RemoteURLAPIGetter(__key),
                RemoteURLEXTGetter(__key),
                PathGetter(__key),
                NameGetter(__key),
            ])

        return getters

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
