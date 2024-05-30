"""
All type hints to use throughout the module.
"""
from collections.abc import MutableMapping
from typing import Any, Mapping

from yarl import URL

from musify.libraries.remote.core import RemoteResponse
from musify.types import UnitMutableSequence, UnitSequence

type APIInputValueSingle[T: RemoteResponse] = str | URL | Mapping[str, Any] | T
type APIInputValueMulti[T: RemoteResponse] = (
        UnitSequence[str] |
        UnitMutableSequence[URL] |
        UnitMutableSequence[MutableMapping[str, Any]] |
        UnitSequence[T]
)
