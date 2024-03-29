"""
All type hints to use throughout the module.
"""
from collections.abc import MutableMapping
from typing import Any, TypeVar

from musify.libraries.remote.core import RemoteResponse
from musify.types import UnitMutableSequence, UnitSequence

UT = TypeVar('UT')
APIInputValue = (
        UnitMutableSequence[str] |
        UnitMutableSequence[MutableMapping[str, Any]] |
        UnitSequence[RemoteResponse]
)
