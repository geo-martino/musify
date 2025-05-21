from typing import ClassVar, Any

from pydantic import Field, computed_field, field_validator

from musify._types import StrippedString
from musify.model.properties import HasSeparableTags
from musify.model.properties.name import HasName


class Genre(HasName):
    """Represents a genre item and its properties."""
    __unique_attributes__ = frozenset({"name"})

    type: ClassVar[str] = "genre"

    name: StrippedString = Field(
        description="The name of this genre.",
        alias="genre",
    )


class HasGenres[T: Genre](HasSeparableTags):
    genres: list[T] = Field(
        description="The genres associated with this resource.",
        default_factory=list[T],
        validation_alias="genre",
    )

    # noinspection PyNestedDecorators
    @field_validator("genres", mode="before", check_fields=True)
    @classmethod
    def _from_string(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return cls._separate_tags(value)

    @computed_field(description="A string representation of all genres associated with this resource")
    @property
    def genre(self) -> str | None:
        return self._join_tags(genre.name for genre in self.genres)
