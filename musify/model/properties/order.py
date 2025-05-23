from __future__ import annotations

from typing import Any, Self

from pydantic import PositiveInt, Field, model_validator

from musify.exception import MusifyValueError
from musify.model import MusifyModel


class Position(MusifyModel):
    """Represents the index position of a resource within a parent resource."""
    number: PositiveInt | None = Field(
        description="The index position of the resource within the parent resource.",
        default=None,
    )
    total: PositiveInt | None = Field(
        description="The total number of resources in the parent resource.",
        default=None,
    )

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @staticmethod
    def _from_number[T](value: T) -> T | dict[str, Any]:
        if not isinstance(value, int | float):
            return value
        return dict(number=int(value))

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @staticmethod
    def _from_numbers[T](value: T) -> T | dict[str, Any]:
        if not isinstance(value, tuple | list):
            return value

        numbers = iter(value)
        return dict(number=next(numbers, None), total=next(numbers, None))

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @staticmethod
    def _from_string[T](value: T) -> T | dict[str, Any]:
        if not isinstance(value, str):
            return value
        numbers = iter(value.split("/"))
        return dict(number=next(numbers), total=next(numbers, None))

    @model_validator(mode="after")
    def _validate_position_is_less_than_total(self) -> Self:
        if self.number is None or self.total is None:
            return self

        if self.number > self.total:
            raise MusifyValueError("Start position cannot be greater than end position.")
        return self
