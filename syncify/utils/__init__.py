from collections.abc import Sequence
from typing import TypeVar

T = TypeVar('T')
UnitList = T | Sequence[T]
Number = int | float
