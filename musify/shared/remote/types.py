from collections.abc import MutableMapping
from typing import Any

from musify.shared.types import UnitMutableSequence

APIMethodInputType = UnitMutableSequence[str] | UnitMutableSequence[MutableMapping[str, Any]]

