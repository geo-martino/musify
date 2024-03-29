"""
All core type hints to use throughout the entire package.
"""
from collections.abc import Iterable, Sequence, MutableSequence, Collection, Mapping, MutableMapping
from typing import TypeVar

UT = TypeVar('UT')
UnitIterable = UT | Iterable[UT]
UnitCollection = UT | Collection[UT]
UnitSequence = UT | Sequence[UT]
UnitMutableSequence = UT | MutableSequence[UT]
UnitList = UT | list[UT]

JSON_VALUE = str | int | float | list | dict | bool | None
JSON = Mapping[str, JSON_VALUE]
MutableJSON = MutableMapping[str, JSON_VALUE]
DictJSON = dict[str, JSON_VALUE]

Number = int | float
