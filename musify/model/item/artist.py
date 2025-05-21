from typing import ClassVar, Any

from pydantic import Field, computed_field, field_validator

from musify._types import StrippedString
from musify.model.item.genre import HasGenres, Genre
from musify.model.properties import HasName, HasSeparableTags, HasRating


class Artist[GT: Genre](HasGenres[GT], HasName, HasRating):
    """Represents an artist item and its properties."""
    type: ClassVar[str] = "artist"

    name: StrippedString = Field(
        description="The name of this artist.",
        alias="artist",
    )


class HasArtists[T: Artist](HasSeparableTags):
    artists: list[T] | None = Field(
        description="The artists associated with this resource.",
        default_factory=list[T],
        validation_alias="artist",
    )

    # noinspection PyNestedDecorators
    @field_validator("artists", mode="before", check_fields=True)
    @classmethod
    def _from_string(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return cls._separate_tags(value)

    @computed_field(description="A string representation of all artists featured on this resource")
    @property
    def artist(self) -> str | None:
        return self._join_tags(self.artists)
