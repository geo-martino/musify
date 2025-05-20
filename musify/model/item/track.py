from typing import ClassVar, Self

from pydantic import Field, model_validator

from musify.model import MusifyMutableSequence
from musify.model._base import _CollectionModel
from musify.model.item.genre import HasGenres
from musify.model.item.artist import HasArtists
from musify.model.item.album import HasAlbum
from musify.model.properties import HasName, Position, HasLength, HasRating, HasReleaseDate, \
    HasImages, KeySignature, HasMutableURI
from musify._types import Resource, StrippedString


class Track(HasArtists, HasAlbum, HasGenres, HasName, HasLength, HasRating, HasReleaseDate, HasImages):
    """Represents a track item and its properties."""
    type: ClassVar[Resource] = Resource.TRACK

    name: StrippedString = Field(
        description="The title of this track.",
        alias="title",
    )
    track: Position | None = Field(
        description="The position this track has on the album it is featured on.",
        default=None,
    )
    bpm: float | None = Field(
        description="The tempo of this track.",
        default=None,
    )
    key: KeySignature | None = Field(
        description="The key of this track.",
        default=None,
    )
    disc: Position | None = Field(
        description="The position of the disc on the album that this track is featured on.",
        default=None,
    )
    comments: list[str] | None = Field(
        description="Freeform comments that are associated with this track.",
        default=None,
    )

    @model_validator(mode="after")
    def _set_track_total_from_album(self) -> Self:
        if self.album is None or (total := self.album.track_total) is None:
            return self

        if self.track is not None:
            self.track.total = total
        elif self.track is None:
            self.track = Position(total=total)

        return self

    @model_validator(mode="after")
    def _set_disc_total_from_album(self) -> Self:
        if self.album is None or (total := self.album.disc_total) is None:
            return self

        if self.disc is not None:
            self.disc.total = total
        elif self.disc is None:
            self.disc = Position(total=total)

        return self

    def __eq__(self, other: Self):
        if self is other:
            return True
        if not isinstance(other, Track):
            return False

        # match on track properties as last resort
        if not self.artists or not other.artists:
            return False

        self_artists = {artist.name for artist in self.artists}
        item_artists = {artist.name for artist in other.artists}

        return self.name == other.name and self_artists & item_artists and self.album == other.album


class HasTracks[KT, VT: Track](_CollectionModel):
    """A mixin class to add a `tracks` property to a MusifyCollection."""
    tracks: MusifyMutableSequence[KT, VT] = Field(
        description="The tracks in this collection",
        default_factory=MusifyMutableSequence,
        frozen=True,
    )
