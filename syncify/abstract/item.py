from abc import ABCMeta, abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping

from syncify.abstract import PrettyPrinter


class Item(PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing an item."""


class ItemCollection(PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing a collection of items."""

    @property
    @abstractmethod
    def items(self) -> List[Item]:
        raise NotImplementedError

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (t for t in self.items)


@dataclass
class Tags:
    """Tags that can be extracted for a given track and their related inferred attributes"""
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
    compilation: Optional[bool]
    comments: Optional[List[str]]

    uri: Optional[str]
    has_uri: Optional[bool]

    image_links: Optional[MutableMapping[str, str]]
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
    rating: Optional[int]


@dataclass
class SyncResult(ABC):
    pass
