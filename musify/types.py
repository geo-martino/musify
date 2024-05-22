"""
All core type hints to use throughout the entire package.
"""
from collections.abc import Iterable, Sequence, MutableSequence, Collection, Mapping, MutableMapping

type UnitIterable[T] = T | Iterable[T]
type UnitCollection[T] = T | Collection[T]
type UnitSequence[T] = T | Sequence[T]
type UnitMutableSequence[T] = T | MutableSequence[T]
type UnitList[T] = T | list[T]

JSON_VALUE = str | int | float | list | dict | bool | None
JSON = Mapping[str, JSON_VALUE]
MutableJSON = MutableMapping[str, JSON_VALUE]
DictJSON = dict[str, JSON_VALUE]

Number = int | float
