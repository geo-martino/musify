from dataclasses import dataclass
from typing import List, Self, Collection, Union

from syncify.enums import SyncifyEnum, EnumNotFoundError
from syncify.utils import make_list


@dataclass(frozen=True)
class TagMap:
    """Map of human-friendly tag name to ID3 tag ids for a given file type"""

    title: List[str]
    artist: List[str]
    album: List[str]
    album_artist: List[str]
    track_number: List[str]
    track_total: List[str]
    genres: List[str]
    year: List[str]
    bpm: List[str]
    key: List[str]
    disc_number: List[str]
    disc_total: List[str]
    compilation: List[str]
    comments: List[str]
    images: List[str]

    def __getitem__(self, key: str) -> List[str]:
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

    def to_tag(self) -> List[str]:
        """
        Returns all human-friendly tag names for a given enum
        e.g. ``track`` returns both ``track_number`` and ``track_total`` tag names
        """
        tags: List[str] = list(TagMap.__annotations__.keys()) + ["uri"]
        if self == self.ALL:
            return tags
        return [tag for tag in tags if tag.startswith(self.name.casefold())]

    @classmethod
    def to_tags(cls, tags: Union[Self, Collection[Self]]) -> List[str]:
        """Convert the given tags to tag names as given by the attributes of an item/collection"""
        if isinstance(tags, cls):
            return tags.to_tag()
        return [t for tag in make_list(tags) for t in tag.to_tag()]


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
