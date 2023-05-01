from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from http.client import HTTPResponse
from io import BytesIO
from typing import Optional, List, Mapping, Set
from urllib.error import URLError
from urllib.request import urlopen

import mutagen
from PIL import Image, UnidentifiedImageError

from syncify.local.files.tags.exception import ImageLoadError, EnumNotFoundError
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


def open_image(image_link: str) -> Image.Image:
    """
    Open Image object from a given URL or file path

    :param image_link: URL or file path of the image
    :returns: The loaded image, image bytes
    """

    try:  # open image from link
        if image_link.startswith("http"):
            response: HTTPResponse = urlopen(image_link)
            image = Image.open(response.read())
            response.close()
        else:
            image = Image.open(image_link)

        return image
    except (URLError, FileNotFoundError, UnidentifiedImageError):
        raise ImageLoadError(f"{image_link} | Failed to open image")


def get_image_bytes(image: Image.Image) -> bytes:
    image_bytes_arr = BytesIO()
    image.save(image_bytes_arr, format=image.format)
    return image_bytes_arr.getvalue()
