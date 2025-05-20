from typing import ClassVar

from pydantic import Field, computed_field

from musify._types import StrippedString, Resource
from musify.model.properties import HasName, HasSeparableTags


class Genre(HasName):
    """Represents a genre item and its properties."""
    __unique_attributes__ = frozenset({"name"})
    type: ClassVar[Resource] = Resource.GENRE

    name: StrippedString = Field(
        description="The name of this genre.",
        alias="genre",
    )


class HasGenres[T: Genre](HasSeparableTags):
    genres: list[T] = Field(
        description="The genres associated with this resource.",
        default_factory=list,
    )

    @computed_field(description="A string representation of all genres associated with this resource")
    @property
    def genre(self) -> str | None:
        return self._join_tags(self.genres)
