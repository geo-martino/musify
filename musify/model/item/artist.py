from typing import ClassVar

from pydantic import Field, computed_field

from musify._types import Resource, StrippedString
from musify.model.item.genre import HasGenres
from musify.model.properties import HasName, HasSeparableTags, HasRating


class Artist(HasGenres, HasName, HasRating):
    """Represents an artist item and its properties."""
    type: ClassVar[Resource] = Resource.ARTIST

    name: StrippedString = Field(
        description="The name of this artist.",
        alias="artist",
    )


class HasArtists[T: Artist](HasSeparableTags):
    artists: list[T] | None = Field(
        description="The artists associated with this resource.",
        default_factory=list,
    )

    @computed_field(description="A string representation of all artists featured on this resource")
    @property
    def artist(self) -> str | None:
        return self._join_tags(self.artists)
