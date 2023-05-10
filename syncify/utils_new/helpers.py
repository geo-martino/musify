from enum import IntEnum
from typing import Any, List, Optional, Set, Self

from syncify.utils_new.exception import EnumNotFoundError


def make_list(data: Any) -> Optional[List]:
    if isinstance(data, list):
        return data
    elif isinstance(data, set):
        return list(data)

    return [data] if data is not None else None


class SyncifyEnum(IntEnum):

    @classmethod
    def all(cls) -> Set[Self]:
        return {e for e in cls if e.name != "ALL"}

    @classmethod
    def from_name(cls, name: str) -> Self:
        """
        Returns the first enum that matches the given name

        :exception EnumNotFoundError: If a corresponding enum cannot be found.
        """
        for enum in cls:
            if name.strip().upper() == enum.name.upper():
                return enum
        raise EnumNotFoundError(name)
