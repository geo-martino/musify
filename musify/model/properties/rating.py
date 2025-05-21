from __future__ import annotations

from pydantic import PositiveFloat, Field

from musify.model import MusifyRootModel
from musify.model._base import _AttributeModel


class Rating(MusifyRootModel[PositiveFloat]):
    pass


class HasRating(_AttributeModel):
    """Represents a resource that has a rating."""
    rating: float | None = Field(
        description="The rating of this resource.",
        default=None,
    )
