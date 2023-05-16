from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping, Collection

from syncify.abstract.item import Item, Base
from syncify.abstract.misc import PrettyPrinter


@dataclass
class ItemCollection(Base, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing a collection of items."""

    @property
    @abstractmethod
    def items(self) -> List[Item]:
        raise NotImplementedError

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (t for t in self.items)

    def __contains__(self, i: Item):
        if i.has_uri and i.uri in [item.uri for item in self.items if item.has_uri]:
            return True
        return False


@dataclass
class Playlist(ItemCollection, metaclass=ABCMeta):
    """A playlist of items and some of their derived properties/objects"""
    description: Optional[str] = None
    track_total: int = 0
    image_links: MutableMapping[str, str] = None
    has_image: bool = False

    length: float = 0
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@dataclass
class Library(ItemCollection, metaclass=ABCMeta):
    """A library of items and playlists"""

    @property
    def playlists(self) -> MutableMapping[str, Playlist]:
        raise NotImplementedError


@dataclass
class Folder(ItemCollection, metaclass=ABCMeta):
    """A folder of items and some of their derived properties/objects"""
    track_total: int = 0
    compilation: bool = False

    artists: Collection = None
    albums: Collection = None
    genres: Collection[str] = None


@dataclass
class Album(ItemCollection, metaclass=ABCMeta):
    """An album of items and some of their derived properties/objects"""
    artist: Optional[str] = None
    album: str = None
    album_artist: Optional[str] = None
    track_total: int = 0
    genres: Collection[str] = None
    year: Optional[int] = None
    disc_total: Optional[int] = None
    compilation: bool = False

    image_links: MutableMapping[str, str] = None
    has_image: bool = False

    length: float = 0
    rating: Optional[float] = None

    artists: Collection = None


@dataclass
class Artist(ItemCollection, metaclass=ABCMeta):
    """An artist of items and some of their derived properties/objects"""
    albums: Collection = None
    genres: Collection[str] = None


@dataclass
class Genre(ItemCollection, metaclass=ABCMeta):
    """A genre of items and some of their derived properties/objects"""
    artists: Collection = None
    albums: Collection = None
    genres: Collection[str] = None
