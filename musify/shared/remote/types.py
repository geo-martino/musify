"""
All type hints to use throughout the module.
"""

from collections.abc import MutableMapping
from typing import Any, TypeVar

from musify.shared.remote import RemoteResponse
from musify.shared.types import UnitMutableSequence, UnitSequence

UT = TypeVar('UT')
APIInputValue = (
        UnitMutableSequence[str] |
        UnitMutableSequence[MutableMapping[str, Any]] |
        UnitSequence[UT: RemoteResponse]
)
