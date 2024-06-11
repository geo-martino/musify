"""
The fundamental core enum classes for the entire package.
"""
from enum import IntEnum
from typing import Self

from musify.exception import MusifyEnumError
from musify.utils import unique_list


class MusifyEnum(IntEnum):
    """Generic class for :py:class:`IntEnum` implementations for the entire package."""

    @classmethod
    def map(cls, enum: Self) -> list[Self]:
        """
        Optional mapper to apply to the enum found during :py:meth:`all`, :py:meth:`from_name`,
        and :py:meth:`from_value` calls
        """
        return [enum]

    @classmethod
    def all(cls) -> list[Self]:
        """Get all enums for this enum."""
        return unique_list(e for enum in cls if enum.name != "ALL" for e in cls.map(enum))

    @classmethod
    def from_name(cls, *names: str, fail_on_many: bool = True) -> list[Self]:
        """
        Returns all enums that match the given enum names

        :param fail_on_many: If more than one enum is found, raise an exception.
        :raise EnumNotFoundError: If a corresponding enum cannot be found.
        """
        names_upper = [name.strip().upper() for name in names]
        enums = unique_list(e for enum in cls if enum.name in names_upper for e in cls.map(enum))

        if len(enums) == 0:
            raise MusifyEnumError(names)
        elif len(enums) > 1 and fail_on_many:
            raise MusifyEnumError(value=enums, message="Too many enums found")

        return enums

    @classmethod
    def from_value(cls, *values: int, fail_on_many: bool = True) -> list[Self]:
        """
        Returns all enums that match the given enum values

        :param fail_on_many: If more than one enum is found, raise an exception.
        :raise EnumNotFoundError: If a corresponding enum cannot be found.
        """
        enums = unique_list(e for enum in cls if enum.value in values for e in cls.map(enum))
        if len(enums) == 0:
            raise MusifyEnumError(values)
        elif len(enums) > 1 and fail_on_many:
            raise MusifyEnumError(value=enums, message="Too many enums found")
        return enums
