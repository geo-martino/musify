from enum import IntEnum
from typing import Self

from syncify.exception import EnumNotFoundError


class SyncifyEnum(IntEnum):
    """Generic class for storing IntEnums."""

    @classmethod
    def all(cls) -> list[Self]:
        """Get all enums for this enum."""
        return [e for e in cls if e.name != "ALL"]

    @classmethod
    def from_name(cls, name: str) -> Self:
        """
        Returns the first enum that matches the given name

        :raise EnumNotFoundError: If a corresponding enum cannot be found.
        """
        for enum in cls:
            if name.strip().upper() == enum.name.upper():
                return enum
        raise EnumNotFoundError(name)
