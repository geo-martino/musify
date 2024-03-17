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

JSON = Mapping[str, str | int | float | list | dict | bool | None]
MutableJSON = MutableMapping[str, str | int | float | list | dict | bool | None]
UnitJSON = UnitMutableSequence[str] | UnitMutableSequence[JSON]
UnitMutableJSON = UnitMutableSequence[str] | UnitMutableSequence[MutableJSON]

Number = int | float
