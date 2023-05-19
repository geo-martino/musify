from __future__ import annotations

from abc import ABCMeta, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping, Collection, Any, Union, Mapping

from syncify.abstract.item import Item, Base
from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName
from syncify.utils import Logger, UnionList, make_list


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

    def merge_items(
            self, items: Union[ItemCollection, Collection[Item]], tags: UnionList[TagName] = TagName.ALL
    ) -> None:
        tags: List[TagName] = make_list(tags)
        if TagName.ALL in tags:
            tag_names = TagName.all()
        else:
            tag_names = [t for tag in tags for t in tag.to_tag()]

        if isinstance(self, Library):
            self.logger.info(f"\33[1;95m  >\33[1;97m "
                             f"Merging library of {len(self)} tracks with {len(items)} tracks on tags: "
                             f"{', '.join(tag_names)} \33[0m")
            items = self.get_progress_bar(iterable=items, desc="Merging library", unit="tracks")

        for item in items:
            item_in_library = next((i for i in self.items if i == item), None)
            if not item_in_library:
                continue

            for tag in tag_names:
                if hasattr(item, tag):
                    setattr(item_in_library, tag, getattr(item, tag))

        if isinstance(self, Library):
            self.print_line()

    def __hash__(self):
        return hash((self.name, (item for item in self.items)))

    def __eq__(self, collection):
        return self.name == collection.name and all(x == y for x, y in zip(self, collection))

    def __ne__(self, item):
        return not self.__eq__(item)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (t for t in self.items)

    def __contains__(self, item: Item):
        return any(item == i for i in self.items)


class BasicCollection(ItemCollection):
    @property
    def name(self) -> str:
        return self._name

    @property
    def items(self) -> List[Item]:
        return self._items

    def __init__(self, name: str, items: List[Item]):
        self._name = name
        self._items = items

    def as_dict(self) -> MutableMapping[str, Any]:
        return {"name": self.name, "items": self.items}


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

    @abstractmethod
    def extend(self, items: Union[ItemCollection, Collection[Item]]) -> None:
        raise NotImplementedError

    def get_filtered_playlists(
            self,
            include: Optional[Collection[str]] = None,
            exclude: Optional[Collection[str]] = None,
            **filter_tags: List[Any]
    ) -> MutableMapping[str, Playlist]:
        """
        Returns the playlists of this library featuring only the items that don't have tags matching those given.
        Parse a tag name as a parameter with its value being a list of tags to filter out of the items
        in the returned playlists

        :return: Filtered playlists.
        """
        self.logger.info(f"\33[1;95m ->\33[1;97m Filtering playlists and tracks from {len(self.playlists)} playlists\n"
                         f"\33[0;90m    Filter out tags: {filter_tags} \33[0m")
        max_width = self.get_max_width(self.playlists)

        filtered = {}
        for name, playlist in self.playlists.items():
            if (include and name not in include) or (exclude and name in exclude):
                continue

            filtered[name] = deepcopy(playlist)
            for item in playlist.items:
                for tag, values in filter_tags.items():
                    value = getattr(item, tag, None)
                    if isinstance(value, str) and value.strip().lower() in values:
                        filtered[name].remove(item)
                        break

            self.logger.debug(f"{self.truncate_align_str(name, max_width=max_width)} | "
                              f"Filtered out {len(filtered[name]) - len(playlist):>3} items")

        self.print_line()
        return filtered

    @abstractmethod
    def merge_playlists(self, playlists: Optional[Union[Library, Mapping[str, Playlist], List[Playlist]]] = None):
        """Merge playlists from given list/map/library to this library"""
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
