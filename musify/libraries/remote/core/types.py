"""
All type hints to use throughout the module.
"""
from collections.abc import MutableMapping
from typing import Any

from yarl import URL

from musify.libraries.remote.core import RemoteResponse
from musify.types import UnitMutableSequence, UnitSequence

type APIInputValue = (
        UnitMutableSequence[str] |
        UnitMutableSequence[URL] |
        UnitMutableSequence[MutableMapping[str, Any]] |
        UnitSequence[RemoteResponse]
)
