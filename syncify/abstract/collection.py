from abc import ABCMeta, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping, Collection, Any

from syncify.abstract.item import Item, Base
from syncify.abstract.misc import PrettyPrinter
from syncify.utils.logger import Logger


@dataclass
class ItemCollection(Base, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing a collection of items."""

    @property
    @abstractmethod
    def items(self) -> List[Item]:
        raise NotImplementedError

    def add(self, item: Item):
        self.items.append(item)

    def add_all(self, items: List[Item]):
        self.items.extend(items)

    def remove(self, item: Item):
        self.items.remove(item)

    def clear(self):
        self.items.clear()

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
class Library(ItemCollection, Logger, metaclass=ABCMeta):
    """A library of items and playlists"""

    @property
    def playlists(self) -> MutableMapping[str, Playlist]:
        raise NotImplementedError

    def get_filtered_playlists(self, **filter_tags: List[Any]) -> MutableMapping[str, Playlist]:
        """
        Returns the playlists of this library featuring only the items that don't have tags matching those given.
        Parse a tag name as a parameter with its value being a list of tags to filter out of the items
        in the returned playlists

        :return: Filtered playlists.
        """
        self._logger.debug(f"Filtering tracks in {len(self.playlists)} playlists | "
                           f"Filter out tags: {filter_tags}")
        max_width = self._get_max_width(self.playlists, max_width=50)

        filtered = {}
        for name, playlist in self.playlists.items():
            filtered[name] = deepcopy(playlist)
            for item in playlist.items:
                for tag, values in filter_tags.items():
                    value = getattr(item, tag, None)
                    if isinstance(value, str) and value.strip().lower() in values:
                        filtered[name].remove(item)
                        break

            self._logger.debug(f"{self._truncate_align_str(name, max_width=max_width)} | "
                               f"Filtered out {len(filtered[name]) - len(playlist):>3} items")
        return filtered


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
