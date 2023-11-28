from dataclasses import dataclass
from typing import Self
from collections.abc import Collection

from . import SyncifyEnum, EnumNotFoundError
from syncify.utils.helpers import to_collection


@dataclass(frozen=True)
class TagMap:
    """Map of human-friendly tag name to ID3 tag ids for a given file type"""

    title: list[str]
    artist: list[str]
    album: list[str]
    album_artist: list[str]
    track_number: list[str]
    track_total: list[str]
    genres: list[str]
    year: list[str]
    bpm: list[str]
    key: list[str]
    disc_number: list[str]
    disc_total: list[str]
    compilation: list[str]
    comments: list[str]
    images: list[str]

    def __getitem__(self, key: str) -> list[str]:
        return getattr(self, key, [])


class Name(SyncifyEnum):
    """Base class for tag/property names of an item."""

    @classmethod
    def from_name(cls, name: str) -> Self:
        """
        Returns the first enum that matches the given name

        :raises EnumNotFoundError: If a corresponding enum cannot be found.
        """
        name = name.strip().upper()
        if name == "ALBUM_ARTIST":
            return TagName.ALBUM_ARTIST

        for enum in cls:
            if enum.name.startswith(name):
                return enum
            elif enum.name.startswith(name.split("_")[0]):
                return enum
        raise EnumNotFoundError(name)

    @classmethod
    def from_value(cls, value: int) -> Self:
        """
        Returns the first enum that matches the given enum value

        :raises EnumNotFoundError: If a corresponding enum cannot be found.
        """
        for enum in cls:
            if enum.value == value:
                return enum
        raise EnumNotFoundError(value)


class TagName(Name):
    """
    Human-friendly enum tag names using condensed names
    e.g. ``track_number`` and ``track_total`` are condensed to just ``track`` here
    """

    ALL = 0

    TITLE = 65
    ARTIST = 32
    ALBUM = 30  # MusicBee album ignoring articles like 'the' and 'a' etc.
    ALBUM_ARTIST = 31
    TRACK = 86
    GENRES = 59
    YEAR = 35
    BPM = 85
    KEY = 900  # unknown MusicBee mapping
    DISC = 3
    COMPILATION = 901  # unknown MusicBee mapping
    COMMENTS = 44
    URI = 902  # no MusicBee mapping
    IMAGES = 903  # unknown MusicBee mapping

    def to_tag(self) -> list[str]:
        """
        Returns all human-friendly tag names for a given enum
        e.g. ``track`` returns both ``track_number`` and ``track_total`` tag names
        """
        tags: list[str] = list(TagMap.__annotations__.keys()) + ["uri"]
        if self == self.ALL:
            return tags
        return [tag for tag in tags if tag.startswith(self.name.casefold())]

    @classmethod
    def to_tags(cls, tags: Self | Collection[Self]) -> list[str]:
        """Convert the given tags to tag names as given by the attributes of an item/collection"""
        if isinstance(tags, cls):
            return tags.to_tag()
        return [t for tag in to_collection(tags) for t in tag.to_tag()]


class PropertyName(Name):
    """Enums for properties that can be extracted from a file"""

    ALL = 200

    # file properties
    PATH = 106
    FOLDER = 179
    FILENAME = 52
    EXT = 100
    SIZE = 7
    LENGTH = 16
    DATE_MODIFIED = 11

    # library properties
    DATE_ADDED = 12
    LAST_PLAYED = 13
    PLAY_COUNT = 14
    RATING = 75
