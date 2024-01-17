"""
All core type hints to use throughout the entire package.
"""

from collections.abc import Iterable, Sequence, MutableSequence, Collection
from typing import TypeVar

UT = TypeVar('UT')
UnitIterable = UT | Iterable[UT]
UnitSequence = UT | Sequence[UT]
UnitMutableSequence = UT | MutableSequence[UT]
UnitCollection = UT | Collection[UT]

Number = int | float
