from collections.abc import Sequence, Collection, MutableSequence, Iterable
from typing import TypeVar

T = TypeVar('T')
UnitIterable = T | Iterable[T]
UnitSequence = T | Sequence[T]
UnitMutableSequence = T | MutableSequence[T]
UnitCollection = T | Collection[T]
Number = int | float
