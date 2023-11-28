from __future__ import annotations

from abc import ABCMeta, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self
from collections.abc import Collection, Mapping

from syncify.abstract.item import Item, BaseObject, Track
from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName
from syncify.spotify.enums import IDType
from syncify.utils import UnitList
from syncify.spotify.utils import validate_id_type
from syncify.utils.logger import Logger


@dataclass
class ItemCollection(BaseObject, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing a collection of items."""

    @property
    @abstractmethod
    def items(self) -> list[Item]:
        """The items in this collection"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """Number of tracks in this collection"""
        return len(self)

    def append(self, item: Item):
        """Append one item to the items in this collection"""
        self.items.append(item)

    def extend(self, items: Self | Collection[Item]):
        """Append many items to the items in this collection"""
        self.items.extend(items)

    def remove(self, item: Item):
        """Remove one item from the items in this collection"""
        self.items.remove(item)

    def clear(self):
        """Remove all items from this collection"""
        self.items.clear()

    def merge_items(self, items: ItemCollection | Collection[Item], tags: UnitList[TagName] = TagName.ALL):
        """
        Merge this collection with another collection or list of items
        by performing an inner join on a given set of tags
        
        :param items: List of items or ItemCollection to merge with
        :param tags: List of tags to merge on. 
        """
        tag_names = set(TagName.to_tags(tags))

        if isinstance(self, Library):  # log status message and use progress bar for libraries
            self.logger.info(
                f"\33[1;95m  >\33[1;97m "
                f"Merging library of {len(self)} items with {len(items)} items on tags: "
                f"{', '.join(tag_names)} \33[0m"
            )
            items = self.get_progress_bar(iterable=items, desc="Merging library", unit="tracks")

        if TagName.IMAGES in tags or TagName.ALL in tags:
            tag_names.add("image_links")
            tag_names.add("has_image")

        for item in items:  # perform the merge
            item_in_library = next((i for i in self.items if i == item), None)
            if not item_in_library:  # skip if the item does not exist in this collection
                continue

            for tag in tag_names:  # merge on each tag
                if hasattr(item, tag):
                    item_in_library[tag] = item[tag]

        if isinstance(self, Library):
            self.print_line()

    def __hash__(self):
        """Uniqueness of collection is a combination of its name and the items it holds"""
        return hash((self.name, (item for item in self.items)))

    def __eq__(self, collection: Self):
        """Names equal and all items equal in order"""
        return (
            self.name == collection.name
            and len(self) == len(collection)
            and all(x == y for x, y in zip(self, collection))
        )

    def __ne__(self, collection: Self):
        return not self.__eq__(collection)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (t for t in self.items)

    def __reversed__(self):
        return reversed(self.items)

    def __contains__(self, item: Item):
        return any(item == i for i in self.items)

    def __getitem__(self, key: str | int | Item) -> Item:
        if isinstance(key, int):  # simply index the list or items
            return self.items[key]
        elif isinstance(key, Item):  # take the URI
            if not key.has_uri or key.uri is None:
                raise KeyError(f"Given item does not have a URI associated: {key.name}")
            key = key.uri
        elif not validate_id_type(key, kind=IDType.URI):  # assume the string is a name
            try:
                return next(item for item in self.items if item.name == key)
            except StopIteration:
                raise KeyError(f"No matching name found: '{key}'")

        try:  # string is a URI
            return next(item for item in self.items if item.uri == key)
        except StopIteration:
            raise KeyError(f"No matching URI found: '{key}'")

    def __setitem__(self, key: str | int | Item, value: Item):
        try:
            value_self = self[key]
        except KeyError:
            if isinstance(key, int):  # don't append if key is index
                raise KeyError(f"Given index is out of range: {key}")
            self.append(value)
            return

        if type(value) is not type(value_self):  # only merge attributes if matching types
            raise ValueError("Trying to set value on mismatched item types")

        for key, value in value.__dict__.items():  # merge attributes
            setattr(value_self, key, deepcopy(value))

    def __delitem__(self, key: str | int | Item):
        del self[key]


class BasicCollection(ItemCollection):
    @property
    def name(self) -> str:
        """The name of this collection"""
        return self._name

    @property
    def items(self) -> list[Item]:
        return self._items

    def __init__(self, name: str, items: list[Item]):
        self._name = name
        self._items = items

    def as_dict(self):
        return {"name": self.name, "items": self.items}


@dataclass
class Playlist(ItemCollection, metaclass=ABCMeta):
    """A playlist of items and some of their derived properties/objects"""
    description: str | None = None
    image_links: Mapping[str, str] = None

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    def has_image(self) -> bool:
        """Does this playlist have an image"""
        return len(self.image_links) > 0

    @property
    def length(self) -> float | None:
        """Total duration of all tracks in this collection in seconds"""
        lengths = {track.length for track in self.tracks}
        return sum(lengths) if lengths else None

    @property
    @abstractmethod
    def date_created(self) -> datetime:
        """datetime object representing when the playlist was created"""
        raise NotImplementedError

    @property
    @abstractmethod
    def date_modified(self) -> datetime:
        """datetime object representing when the playlist was last modified"""
        raise NotImplementedError


class Library(ItemCollection, Logger, metaclass=ABCMeta):
    """A library of items and playlists"""

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks in this library"""
        raise NotImplementedError

    @property
    def playlists(self) -> Mapping[str, Playlist]:
        """The playlists in this library"""
        raise NotImplementedError

    def get_filtered_playlists(
            self,
            include: Collection[str] | None = None,
            exclude: Collection[str] | None = None,
            **filter_tags: list[Any]
    ) -> Mapping[str, Playlist]:
        """
        Returns a filtered set of playlists in this library.
        The playlists returned are deep copies of the playlists in the library.

        :param include: An optional list of playlist names to include.
        :param exclude: An optional list of playlist names to exclude.
        :param filter_tags: Provide optional kwargs of the tags and values of items to filter out of every playlist.
            Parse a tag name as a parameter, any item matching the values given for this tag will be filtered out.
        :return: Filtered playlists.
        """
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Filtering playlists and tracks from {len(self.playlists)} playlists\n"
            f"\33[0;90m    Filter out tags: {filter_tags} \33[0m"
        )
        max_width = self.get_max_width(self.playlists)
        bar = self.get_progress_bar(iterable=self.playlists.items(), desc="Filtering playlists", unit="playlists")

        filtered = {}
        for name, playlist in bar:
            if (include and name not in include) or (exclude and name in exclude):
                continue

            filtered[name] = deepcopy(playlist)
            for item in playlist.items:
                for tag, filter_vals in filter_tags.items():
                    item_val = item[tag]
                    if isinstance(item_val, str):
                        if any(v.strip().lower() in item_val.strip().lower() for v in filter_vals):
                            filtered[name].remove(item)
                            break

            self.logger.debug(
                f"{self.align_and_truncate(name, max_width=max_width)} | "
                f"Filtered out {len(playlist) - len(filtered[name]):>3} items"
            )

        self.print_line()
        return filtered

    @abstractmethod
    def merge_playlists(self, playlists: Self | Mapping[str, Playlist] | list[Playlist] | None = None):
        """Merge playlists from given list/map/library to this library"""
        raise NotImplementedError


class Folder(ItemCollection, metaclass=ABCMeta):
    """A folder of items and some of their derived properties/objects"""

    @property
    def folder(self) -> str:
        """The folder name"""
        return self.name

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str]:
        """List of albums ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    def length(self) -> float | None:
        """Total duration of all tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def compilation(self) -> bool:
        """Is this collection a compilation"""
        raise NotImplementedError


class Album(ItemCollection, metaclass=ABCMeta):
    """An album of items and some of their derived properties/objects"""

    @property
    def album(self) -> str:
        """The album name"""
        return self.name

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    def artist(self) -> str:
        """Joined string representation of all artists in this collection ordered by frequency of appearance"""
        return self._list_sep.join(self.artists)

    @property
    @abstractmethod
    def album_artist(self) -> str | None:
        """The album artist for this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def year(self) -> int | None:
        """The year this collection was released"""
        raise NotImplementedError

    @property
    def disc_total(self) -> int | None:
        """The highest value of disc number in this collection"""
        disc_numbers = {track.disc_number for track in self.tracks if track.disc_number}
        return max(disc_numbers) if disc_numbers else None

    @property
    @abstractmethod
    def compilation(self) -> bool:
        """Is this collection a compilation"""
        raise NotImplementedError

    @property
    @abstractmethod
    def image_links(self) -> Mapping[str, str]:
        """The images associated with this collection in the form ``{image name: image link}``"""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_image(self) -> bool:
        """Does this collection have an image"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all tracks in this collection in seconds"""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> float | None:
        """Rating of this collection"""
        raise NotImplementedError


class Artist(ItemCollection, metaclass=ABCMeta):
    """An artist of items and some of their derived properties/objects"""

    @property
    def artist(self) -> str:
        """The artist name"""
        return self.name

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str]:
        """List of albums ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all tracks in this collection"""
        raise NotImplementedError

    @property
    def rating(self) -> float | None:
        """Rating of this collection"""
        raise NotImplementedError


class Genre(ItemCollection, metaclass=ABCMeta):
    """A genre of items and some of their derived properties/objects"""

    @property
    def genre(self) -> str:
        """The genre name"""
        return self.name

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str]:
        """List of albums ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks in this collection"""
        raise NotImplementedError
