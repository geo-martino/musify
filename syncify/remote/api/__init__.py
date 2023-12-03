from collections.abc import MutableMapping
from typing import Any

from syncify.utils import UnitMutableSequence

APIMethodInputType = UnitMutableSequence[str] | UnitMutableSequence[MutableMapping[str, Any]]
