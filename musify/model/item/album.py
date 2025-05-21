from typing import ClassVar, Any

from pydantic import Field, PositiveInt, field_validator

from musify._types import StrippedString
from musify.model._base import _AttributeModel
from musify.model.item.artist import HasArtists, Artist
from musify.model.item.genre import HasGenres, Genre
from musify.model.properties import HasName, HasLength, HasRating, HasReleaseDate, HasImages, HasSeparableTags


class Album[RT: Artist, GT: Genre](
    HasArtists[RT], HasGenres[GT], HasName, HasLength, HasRating, HasReleaseDate, HasImages
):
    type: ClassVar[str] = "album"

    name: StrippedString = Field(
        description="The name of this album.",
        alias="album",
    )
    compilation: bool | None = Field(
        description="Is this a compilation album",
        default=None,
    )
    track_total: PositiveInt | None = Field(
        description="The total number of tracks on this album",
        default=None,
    )
    disc_total: PositiveInt | None = Field(
        description="The total number of discs for this album",
        default=None,
    )


class HasAlbum[T: Album](_AttributeModel):
    album: T | None = Field(
        description="The album associated with this resource.",
        default=None,
    )


class HasAlbums[T: Album](HasSeparableTags):
    albums: list[T] = Field(
        description="The albums associated with this resource.",
        default=None,
        validation_alias="album",
    )

    # noinspection PyNestedDecorators
    @field_validator("albums", mode="before", check_fields=True)
    @classmethod
    def _from_string(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return cls._separate_tags(value)
