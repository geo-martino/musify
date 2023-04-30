from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Mapping

import mutagen

from syncify.utils.logger import Logger


@dataclass
class TagMap:
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
    images: List[str]
    comments: List[str]


class TagEnums(Enum):
    TITLE = 0
    ARTIST = 1
    ALBUM = 2
    ALBUM_ARTIST = 3
    TRACK = 4
    GENRES = 5
    YEAR = 6
    BPM = 7
    KEY = 8
    DISC = 9
    COMPILATION = 10
    IMAGE = 11
    COMMENTS = 12
    URI = 13


@dataclass
class Tags:
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    album_artist: Optional[str]
    track_number: Optional[int]
    track_total: Optional[int]
    genres: Optional[List[str]]
    year: Optional[int]
    bpm: Optional[float]
    key: Optional[str]
    disc_number: Optional[int]
    disc_total: Optional[int]
    compilation: bool
    image_urls: Optional[Mapping[str, str]]
    has_image: bool
    comments: Optional[List[str]]

    uri: Optional[str]
    has_uri: bool


@dataclass
class Properties:
    # file properties
    path: Optional[str]
    folder: Optional[str]
    filename: Optional[str]
    ext: Optional[str]
    size: Optional[int]
    length: Optional[float]
    date_modified: Optional[datetime]

    # library properties
    date_added: Optional[datetime]
    last_played: Optional[datetime]
    play_count: Optional[int]
    rating: Optional[int]


class TrackBase(Logger, Tags, Properties, metaclass=ABCMeta):

    uri_tag = TagEnums.COMMENTS

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
    def _unavailable_uri_value(self) -> str:
        """Placeholder URI tag for tracks which aren't on Spotify"""
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
        """
