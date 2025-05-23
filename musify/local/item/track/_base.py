from collections.abc import Collection
from typing import Self, Any

import mutagen
from pydantic import field_validator

from musify.local._base import LocalResource
from musify.local.item.album import LocalAlbum
from musify.local.item.artist import LocalArtist
from musify.local.item.genre import LocalGenre
from musify.model.item.track import Track
from musify.model.properties.file import IsFile
from musify.model.properties.uri import HasMutableURI


class LocalTrack[T: mutagen.FileType](LocalResource, Track[LocalArtist, LocalAlbum, LocalGenre], IsFile, HasMutableURI):
    def from_mutagen_file(self, file: T) -> Self:
        pass

    # noinspection PyNestedDecorators
    @field_validator(
        "name", "artists", "album", "genres", "track", "disc", "bpm", "key", "released_at", "uri",
        mode="before", check_fields=False
    )
    @staticmethod
    def _extract_first_value_from_single_sequence(value: Any) -> str | None:
        if isinstance(value, tuple | list) and len(value) == 1:
            value = value[0]
        return value

    # noinspection PyNestedDecorators
    @field_validator(
        "title", "artists", "album", "genres", "track", "disc", "bpm", "key", "released_at", "uri",
        mode="before", check_fields=False
    )
    @staticmethod
    def _convert_null_like_tag_values_to_null(value: Any) -> str | None:
        match value:
            case Collection() if len(value) == 0:
                return
            case Collection() if all(isinstance(v, str) and not v for v in value):
                return
            case _:
                return value

    # noinspection PyNestedDecorators
    @field_validator(
        "title", "album", "bpm", "key", "uri",
        mode="before", check_fields=False
    )
    @staticmethod
    def _extract_first_value_from_sequence(value: Any) -> str | None:
        if isinstance(value, tuple | list):
            value = value[0]
        return value

    def load(self, *args, **kwargs) -> Any:
        pass

    def save(self, *args, **kwargs) -> Any:
        pass
