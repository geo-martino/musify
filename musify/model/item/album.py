from abc import ABC, abstractmethod
from typing import ClassVar, Any

from pydantic import Field, PositiveInt, field_validator, computed_field

from musify._types import StrippedString
from musify.model._base import _AttributeModel, writeable_computed_field
from musify.model.item.artist import HasArtists, Artist
from musify.model.item.genre import HasGenres, Genre
from musify.model.properties import HasName, HasLength, HasRating, HasReleaseDate, HasImages, HasSeparableTags


class _Album[RT: Artist, GT: Genre](
    ABC, HasArtists[RT], HasGenres[GT], HasName, HasLength, HasRating, HasReleaseDate, HasImages
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

    @computed_field(
        description="The total number of tracks on this album",
    )
    @property
    @abstractmethod
    def track_total(self) -> PositiveInt | None:
        """The total number of tracks on this album"""
        raise NotImplementedError

    @computed_field(
        description="The total number of discs for this album",
    )
    @property
    @abstractmethod
    def disc_total(self) -> PositiveInt | None:
        """The total number of discs on this album"""
        raise NotImplementedError


class Album[RT: Artist, GT: Genre](_Album[RT, GT]):

    track_total = writeable_computed_field("track_total")
    disc_total = writeable_computed_field("disc_total")


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
