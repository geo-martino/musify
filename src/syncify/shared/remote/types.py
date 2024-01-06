from collections.abc import MutableMapping
from typing import Any

from syncify.shared.types import UnitMutableSequence

APIMethodInputType = UnitMutableSequence[str] | UnitMutableSequence[MutableMapping[str, Any]]

