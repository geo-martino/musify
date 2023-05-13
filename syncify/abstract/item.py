from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping, Collection

from syncify.abstract.misc import PrettyPrinter


@dataclass
class Tags:
    """Tags that can be extracted for a given track and their related inferred attributes"""
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    album_artist: Optional[str]
    track_number: Optional[int]
    track_total: Optional[int]
    genres: Optional[Collection[str]]
    year: Optional[int]
    bpm: Optional[float]
    key: Optional[str]
    disc_number: Optional[int]
    disc_total: Optional[int]
    compilation: Optional[bool]
    comments: Optional[List[str]]
    image_links: MutableMapping[str, str]
    has_image: bool


@dataclass
class Properties:
    """Properties that can be extracted from a file"""
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
    rating: Optional[float]


class Base:
    list_sep = "; "

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class Item(Base, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing an item."""

    def __init__(self, uri: Optional[str] = None, has_url: Optional[bool] = None):
        self.uri = uri
        self.has_uri = has_url

    def __hash__(self):
        return hash(self.uri)

    def __eq__(self, item):
        return self.uri == item.uri

    def __ne__(self, item):
        return not self.__eq__(item)


class Track(Item, Tags, metaclass=ABCMeta):
    pass
