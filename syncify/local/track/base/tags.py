from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Self

import mutagen

from syncify.abstract import Track, SyncifyEnum, EnumNotFoundError


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


class Name(SyncifyEnum):

    @classmethod
    def from_name(cls, name: str) -> Self:
        """
        Returns the first enum that matches the given name

        :exception EnumNotFoundError: If a corresponding enum cannot be found.
        """
        for enum in cls:
            if enum.name.startswith(name.split("_")[0].upper()):
                return enum
        raise EnumNotFoundError(name)

    @classmethod
    def from_value(cls, value: int) -> Self:
        """
        Returns the first enum that matches the given enum value

        :exception EnumNotFoundError: If a corresponding enum cannot be found.
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
        return [tag for tag in TagMap.__annotations__ if tag.startswith(self.name.lower())]


class PropertyName(Name):
    """Enums for properties that can be extracted from a file"""

    ALL = 0

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


class TagProcessor(Track, metaclass=ABCMeta):
    """Generic base class for tag processing"""

    uri_tag = TagName.COMMENTS

    @property
    @abstractmethod
    def _num_sep(self) -> str:
        """
        Some number values come as a combined string i.e. track number/track total
        Define the separator to use when representing both values as a combined string
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def tag_map(self) -> TagMap:
        raise NotImplementedError

    @property
    @abstractmethod
    def path(self) -> Optional[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def file(self) -> Optional[mutagen.File]:
        raise NotImplementedError

    @abstractmethod
    def load_file(self) -> Optional[mutagen.File]:
        """
        Load local file using mutagen and set object file path and extension properties.

        :returns: Mutagen file object or None if load error.
        :exception FileNotFoundError: If the file cannot be found.
        :exception IllegalFileTypeError: If the file type is not supported.
        """
