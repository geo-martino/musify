from typing import ClassVar

from pydantic import Field, PositiveInt

from musify._types import Resource, StrippedString
from musify.model._base import _AttributeModel
from musify.model.item.artist import HasArtists
from musify.model.item.genre import HasGenres
from musify.model.properties import HasName, HasLength, HasRating, HasReleaseDate, HasImages


class Album(HasArtists, HasGenres, HasName, HasLength, HasRating, HasReleaseDate, HasImages):
    """Represents an album item and its properties."""
    type: ClassVar[Resource] = Resource.ALBUM

    name: StrippedString = Field(
        description="The name of this album.",
        alias="album",
    )
    track_total: PositiveInt | None = Field(
        description="The total number of tracks on this album",
        default=None,
    )
    disc_total: PositiveInt | None = Field(
        description="The total number of discs for this album",
        default=None,
    )
    compilation: bool | None = Field(
        description="Is this a compilation album",
        default=None,
    )


class HasAlbum[T: Album](_AttributeModel):
    album: T | None = Field(
        description="The album associated with this resource.",
        default=None,
    )


class HasAlbums[T: Album](_AttributeModel):
    albums: list[T] | None = Field(
        description="The albums associated with this resource.",
        default=None,
    )
