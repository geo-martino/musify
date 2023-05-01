from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Optional, List, Mapping, Set

from syncify.local.files.utils.exception import EnumNotFoundError


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
    comments: List[str]
    images: List[str]


class TagEnums(IntEnum):
    ALL = 0
    TITLE = 1
    ARTIST = 2
    ALBUM = 3
    ALBUM_ARTIST = 4
    TRACK = 5
    GENRES = 6
    YEAR = 7
    BPM = 8
    KEY = 9
    DISC = 10
    COMPILATION = 11
    COMMENTS = 12
    URI = 13
    IMAGES = 14

    @classmethod
    def all(cls) -> Set[TagEnums]:
        all_enums = set(cls)
        all_enums.remove(cls.ALL)
        return all_enums

    @classmethod
    def to_tag(cls, enum: TagEnums) -> Set[str]:
        return set(tag for tag in TagMap.__annotations__ if tag.startswith(enum.name.lower()))

    @classmethod
    def to_enum(cls, name: str) -> TagEnums:
        results = [enum for enum in cls if enum.name.startswith(name.split("_")[0].upper())]
        if len(results) == 0:
            raise EnumNotFoundError(name)
        return results[0]


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
    comments: Optional[List[str]]

    uri: Optional[str]
    has_uri: bool

    image_links: Optional[Mapping[str, str]]
    has_image: bool


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
