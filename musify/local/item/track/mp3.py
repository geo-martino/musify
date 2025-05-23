from collections.abc import MutableSequence, MutableMapping, Iterable
from typing import Any

import mutagen.id3
import mutagen.mp3
from PIL import Image
from pydantic import Field, AliasChoices, PositiveFloat, InstanceOf, model_validator, field_validator

from musify.local.item.album import LocalAlbum
from musify.local.item.artist import LocalArtist
from musify.local.item.genre import LocalGenre
from musify.local.item.track import LocalTrack
from musify.model.properties.date import SparseDate
from musify.model.properties.image import ImageLink
from musify.model.properties.music import KeySignature
from musify.model.properties.order import Position


class MP3(LocalTrack[mutagen.mp3.MP3]):
    name: str | None = Field(
        description="A title of this track.",
        default=None,
        validation_alias="TIT2"
    )
    artists: list[LocalArtist] | None = Field(
        description="The artists featured on this track.",
        default=None,
        validation_alias="TPE1"
    )
    album: LocalAlbum | None = Field(
        description="The album this track is featured on.",
        default=None,
        validation_alias="TALB"
    )
    # album_artist: LocalArtist | None = Field(
    #     default=None,
    #     validation_alias="TPE2"
    # )
    genres: list[LocalGenre] | None = Field(
        description="The genres associated with this track.",
        default=None,
        validation_alias="TCON"
    )
    track: Position | None = Field(
        description="The position of the track on the album that this track is featured on.",
        default=None,
        validation_alias="TRCK"
    )
    disc: Position | None = Field(
        description="The position of the disc in the album that this track is featured on.",
        default=None,
        validation_alias="TPOS"
    )
    bpm: PositiveFloat | None = Field(
        description="The tempo of this track.",
        default=None,
        validation_alias="TBPM"
    )
    key: KeySignature | None = Field(
        description="The key of this track.",
        default=None,
        validation_alias="TKEY"
    )
    released_at: SparseDate | None = Field(
        description="The date this item was released.",
        default=None,
        validation_alias=AliasChoices("TDRC", "TDAT", "TDOR", "TYER", "TORY")
    )
    comments: list[str] | None = Field(
        description="Freeform comments that are associated with this track.",
        default=None,
        validation_alias=AliasChoices("COMM", "COMMENT")
    )
    images: list[InstanceOf[Image.Image] | ImageLink] | None = Field(
        description="Images associated with this track.",
        default=None,
        validation_alias="APIC"
    )
    # compilation: list[str] | None = Field(
    #     default=None,
    #     validation_alias="TCMP"
    # )

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def _merge_suffixed_tag_keys[T](cls, data: T) -> T | dict[str, Any]:
        # parent class validators always execute after child class validators
        # need to manually call required upstream parent validators here
        # noinspection PyCallingNonCallable
        data = cls._from_mutagen(data)
        if not isinstance(data, MutableMapping):
            return data

        for key in list(data):
            key_prefix = key.split(":")[0]
            if key_prefix.startswith("COMM"):  # special case to merge comment keys correctly
                key_prefix = "COMM"
            if key_prefix == key:
                continue

            if key_prefix not in data:
                data[key_prefix] = []
            elif not isinstance(val_prefix := data[key_prefix], MutableSequence):
                data[key_prefix] = [val_prefix]

            data[key_prefix].append(data.pop(key))

        return data

    # noinspection PyNestedDecorators
    @field_validator(
        "name", "album", "track", "disc", "bpm", "key", "released_at", "uri",
        mode="before"
    )
    @classmethod
    def _from_text_frame[T](cls, value: T | Iterable[T]) -> T | str:
        # parent class validators always execute after child class validators
        # need to manually call required upstream parent validators here
        value = cls._extract_first_value_from_single_sequence(value)
        if not isinstance(value, mutagen.id3.TextFrame):
            return value

        return str(value)

    # noinspection PyNestedDecorators
    @field_validator(
        "artists", "genres", "comments",
        mode="before"
    )
    @classmethod
    def _from_text_frames[T](cls, value: T | Iterable[T]) -> T | list[str]:
        if value is None:
            return value
        if not isinstance(value, tuple | list):
            value = [value]

        return [cls._from_text_frame(v) for v in value]

    # noinspection PyNestedDecorators
    @field_validator("images", mode="before")
    @classmethod
    def _extract_images[T](cls, value: T | Iterable[T]) -> T | list[T | bytes]:
        if value is None:
            return value
        if not isinstance(value, tuple | list):
            value = [value]

        # noinspection PyUnresolvedReferences
        return [attr.data if isinstance(attr, mutagen.id3.APIC) else attr for attr in value]
