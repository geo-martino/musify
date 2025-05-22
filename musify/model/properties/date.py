from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import PositiveInt, Field

from musify.model import MusifyModel
from musify.model._base import _AttributeModel


class SparseDate(MusifyModel):
    """
    A sparse date represents a date which may not have all parts to make up a full date.

    This allows for defining a date as just the year, or just the year and month,
    while also allowing for a full date definition of year, month, and day.
    """
    year: PositiveInt = Field(
        description="The year.",
    )
    month: Annotated[int, Field(ge=1, le=12)] | None = Field(
        description="The month.",
        default=None,
    )
    day: Annotated[int, Field(ge=1, le=31)] | None = Field(
        description="The day.",
        default=None,
    )

    @property
    def date(self) -> date | None:
        """A :py:class:`date` object representing the full date definition if available."""
        if self.year and self.month and self.day:
            return date(self.year, self.month, self.day)


class HasReleaseDate(_AttributeModel):
    """Represents a resource that has an associated release date."""
    released_at: SparseDate | None = Field(
        description="The date this item was released.",
        default=None,
    )
