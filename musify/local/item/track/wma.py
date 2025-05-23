import struct
from collections.abc import Iterable
from io import BytesIO

import mutagen.asf
import mutagen.id3
from PIL import Image, UnidentifiedImageError
from pydantic import Field, AliasChoices, PositiveFloat, InstanceOf, field_validator

from musify.local.item.album import LocalAlbum
from musify.local.item.artist import LocalArtist
from musify.local.item.genre import LocalGenre
from musify.local.item.track import LocalTrack
from musify.model.properties.date import SparseDate
from musify.model.properties.image import ImageLink
from musify.model.properties.music import KeySignature
from musify.model.properties.order import Position


class WMA(LocalTrack[mutagen.asf.ASF]):
    name: str | None = Field(
        description="A title of this track.",
        default=None,
        validation_alias="Title"
    )
    artists: list[LocalArtist] | None = Field(
        description="The artists featured on this track.",
        default=None,
        validation_alias="Author"
    )
    album: LocalAlbum | None = Field(
        description="The album this track is featured on.",
        default=None,
        validation_alias="WM/AlbumTitle"
    )
    # album_artist: list[LocalAlbum] | None = Field(
    #     default=None,
    #     validation_alias="WM/AlbumArtist"
    # )
    genres: list[LocalGenre] | None = Field(
        description="The genres associated with this track.",
        default=None,
        validation_alias="WM/Genre"
    )
    track: Position | None = Field(
        description="The position of the track on the album that this track is featured on.",
        default=None,
        validation_alias=AliasChoices("WM/TrackNumber", "TotalTracks")
    )
    disc: Position | None = Field(
        description="The position of the disc in the album that this track is featured on.",
        default=None,
        validation_alias="WM/PartOfSet"
    )
    bpm: PositiveFloat | None = Field(
        description="The tempo of this track.",
        default=None,
        validation_alias="WM/BeatsPerMinute"
    )
    key: KeySignature | None = Field(
        description="The key of this track.",
        default=None,
        validation_alias="WM/InitialKey"
    )
    released_at: SparseDate | None = Field(
        description="The date this item was released.",
        default=None,
        validation_alias=AliasChoices("WM/Year", "WM/OriginalReleaseYear")
    )
    comments: list[str] | None = Field(
        description="Freeform comments that are associated with this track.",
        default=None,
        validation_alias=AliasChoices("Description", "WM/Comments")
    )
    images: list[InstanceOf[Image.Image] | ImageLink] | None = Field(
        description="Images associated with this track.",
        default=None,
        validation_alias="WM/Picture"
    )
    # compilation: list[str] | None = Field(
    #     default=None,
    #     validation_alias="COMPILATION"
    # )

    # noinspection PyNestedDecorators
    @field_validator(
        "name", "album", "track", "disc", "bpm", "key", "released_at", "uri",
        mode="before"
    )
    @classmethod
    def _from_unicode_attribute[T](cls, value: T) -> T | str:
        # parent class validators always execute after child class validators
        # need to manually call required upstream parent validators here
        value = cls._extract_first_value_from_single_sequence(value)
        if not isinstance(value, mutagen.asf.ASFUnicodeAttribute):
            return value

        return value.value

    # noinspection PyNestedDecorators
    @field_validator(
        "artists", "genres", "comments",
        mode="before"
    )
    @classmethod
    def _from_unicode_attributes[T](cls, value: T) -> T | list[str]:
        if not isinstance(value, tuple | list):
            return value
        return [cls._from_unicode_attribute(v) for v in value]

    # noinspection PyNestedDecorators
    @field_validator("images", mode="before")
    @classmethod
    def _extract_images[T](cls, data: T | Iterable[T]) -> T | list[T | bytes]:
        if data is None:
            return
        if not isinstance(data, tuple | list):
            data = [data]

        values_converted: list[T | bytes] = []
        for attribute in data:
            if isinstance(attribute, mutagen.asf.ASFByteArrayAttribute):
                attribute = attribute.value

            id3_type, size = struct.unpack_from(b"<bi", attribute)
            id3_types = {
                int(val) for val in vars(mutagen.id3.PictureType).values() if isinstance(val, mutagen.id3.PictureType)
            }
            if id3_type not in id3_types:
                # bytes does not have WMA-spec header, assume bytes are raw image data
                values_converted.append(attribute)
                continue

            # extract WMA-spec header information
            pos = 5
            mime = b""
            while attribute[pos:pos + 2] != b"\x00\x00":
                mime += attribute[pos:pos + 2]
                pos += 2

            pos += 2
            description = b""

            while attribute[pos:pos + 2] != b"\x00\x00":
                description += attribute[pos:pos + 2]
                pos += 2
            pos += 2

            print(id3_type, size, pos)
            print(attribute[:pos])

            attribute_bytes = attribute[pos:pos + size]
            values_converted.append(attribute_bytes)

        return values_converted
