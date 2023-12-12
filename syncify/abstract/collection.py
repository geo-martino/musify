from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping, Iterable, Container, MutableSequence
from copy import deepcopy
from datetime import datetime
from typing import Any, Self, SupportsIndex, Hashable

from syncify.processors.sort import ItemSorter, ShuffleMode, ShuffleBy
from syncify.remote.enums import RemoteIDType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitIterable, UnitSequence
from syncify.utils.helpers import to_collection
from syncify.utils.logger import Logger
from .enums import Field, FieldCombined, TagField
from .item import Item, Track, ObjectPrinterMixin


# noinspection PyShadowingNames
class ItemCollection[T: Item](ObjectPrinterMixin, MutableSequence[T], Hashable, metaclass=ABCMeta):
    """
    Generic class for storing a collection of items.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on items.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    """

    @property
    @abstractmethod
    def items(self) -> list[T]:
        """The items in this collection"""
        raise NotImplementedError

    def __init__(self, remote_wrangler: RemoteDataWrangler = None):
        super().__init__()
        self.remote_wrangler = remote_wrangler

    def index(self, __item: T, __start: SupportsIndex = None, __stop: SupportsIndex = None) -> int:
        """
        Return first index of item from items in this collection.

        :raise ValueError: If the value is not present.
        """
        return self.items.index(__item, __start if __start else 0, __stop if __stop else len(self.items))

    def count(self, __item: T) -> int:
        """Return the number of occurrences of the given :py:class:`Item` in this collection"""
        return self.items.count(__item)

    def copy(self) -> list[T]:
        """Return a shallow copy of the list of items in this collection"""
        return [item for item in self.items]

    def append(self, __item: T, allow_duplicates: bool = True) -> None:
        """Append one item to the items in this collection"""
        if allow_duplicates or __item not in self.items:
            self.items.append(__item)

    def extend(self, __items: Iterable[T], allow_duplicates: bool = True) -> None:
        """Append many items to the items in this collection"""
        if isinstance(__items, ItemCollection):
            __items = __items.items

        if allow_duplicates:
            self.items.extend(__items)
        else:
            self.items.extend(item for item in __items if item not in self.items)

    def insert(self, __index: int, __item: T, allow_duplicates: bool = True) -> None:
        """Insert given :py:class:`Item` before the given index"""
        if allow_duplicates or __item not in self.items:
            self.items.insert(__index, __item)

    def remove(self, __item: T) -> None:
        """Remove one item from the items in this collection"""
        self.items.remove(__item)

    def pop(self, __item: SupportsIndex = None) -> T:
        """Remove one item from the items in this collection and return it"""
        return self.items.pop(__item) if __item else self.items.pop()

    def reverse(self) -> None:
        """Reverse the order of items in this collection in-place"""
        self.items.reverse()

    def clear(self) -> None:
        """Remove all items from this collection"""
        self.items.clear()

    def sort(
            self,
            fields: UnitSequence[Field | None] | Mapping[Field | None, bool] = (),
            shuffle_mode: ShuffleMode = ShuffleMode.NONE,
            shuffle_by: ShuffleBy = ShuffleBy.TRACK,
            shuffle_weight: float = 1.0,
            key: Field | None = None,
            reverse: bool = False,
    ) -> None:
        """
        Sort items in this collection in-place based on given conditions.
        If key is given,

        :param fields:
            * When None and ShuffleMode is RANDOM, shuffle the tracks. Otherwise, do nothing.
            * List of tags/properties to sort by.
            * Map of {``tag/property``: ``reversed``}. If reversed is true, sort the ``tag/property`` in reverse.
        :param shuffle_mode: The mode to use for shuffling.
        :param shuffle_by: The field to shuffle by when shuffling.
        :param shuffle_weight: The weights (between 0 and 1) to apply to shuffling modes that can use it.
            This value will automatically be limited to within the accepted range 0 and 1.
        :param key: Tag or property to sort on. Can be given instead of ``fields`` for a simple sort.
            If set, all other fields apart from ``reverse`` are ignored.
            If None, ``fields``, ``shuffle_mode``, ``shuffle_by``, and ``shuffle_weight`` are used to apply sorting.
        :param reverse: If true, reverse the order of the sort at the end.
        """
        if key is not None:
            ItemSorter.sort_by_field(self.items, field=key)
        else:
            ItemSorter(
                fields=fields, shuffle_mode=shuffle_mode, shuffle_by=shuffle_by, shuffle_weight=shuffle_weight
            ).sort(self.items)

        if reverse:
            self.items.reverse()

    def merge_items(self, items: Collection[T], tags: UnitIterable[TagField] = FieldCombined.ALL) -> None:
        """
        Merge this collection with another collection or list of items
        by performing an inner join on a given set of tags
        
        :param items: List of items or ItemCollection to merge with
        :param tags: List of tags to merge on. 
        """
        # noinspection PyTypeChecker
        tag_names = set(TagField.__tags__) if tags == FieldCombined.ALL else set(TagField.to_tags(tags))

        if isinstance(self, Library):  # log status message and use progress bar for libraries
            self.logger.info(
                f"\33[1;95m  >\33[1;97m "
                f"Merging library of {len(self)} items with {len(items)} items on tags: "
                f"{', '.join(tag_names)} \33[0m"
            )
            items = self.get_progress_bar(iterable=items, desc="Merging library", unit="tracks")

        tags = to_collection(tags)
        if FieldCombined.IMAGES in tags or FieldCombined.ALL in tags:
            tag_names.add("image_links")
            tag_names.add("has_image")

        for item in items:  # perform the merge
            item_in_collection = next((i for i in self.items if i == item), None)
            if not item_in_collection:  # skip if the item does not exist in this collection
                continue

            for tag in tag_names:  # merge on each tag
                if hasattr(item, tag):
                    item_in_collection[tag] = item[tag]

        if isinstance(self, Library):
            self.print_line()

    def __hash__(self):
        """Uniqueness of collection is a combination of its name and the items it holds"""
        return hash((self.name, len(self.items), (item for item in self.items)))

    def __eq__(self, __collection: ItemCollection | Iterable[T]):
        """Names equal and all items equal in order"""
        name = self.name == __collection.name if isinstance(__collection, ItemCollection) else True
        length = len(self) == len(__collection)
        items = all(x == y for x, y in zip(self, __collection))
        return name and length and items

    def __ne__(self, __collection: ItemCollection | Iterable[T]):
        return not self.__eq__(__collection)

    def __iadd__(self, __items: Iterable[T]):
        self.extend(__items)
        return self

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (t for t in self.items)

    def __reversed__(self):
        return reversed(self.items)

    def __contains__(self, __item: T):
        return any(__item == i for i in self.items)

    def __getitem__(self, __key: str | int | slice | Item) -> T | MutableSequence[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI.
        If an item is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri or __key.uri is None:
                raise KeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri
        elif self.remote_wrangler is None or not self.remote_wrangler.validate_id_type(__key, kind=RemoteIDType.URI):
            # assume the string is a name
            try:
                return next(item for item in self.items if item.name == __key)
            except StopIteration:
                raise KeyError(f"No matching name found: '{__key}'")

        try:  # string is a URI
            return next(item for item in self.items if item.uri == __key)
        except StopIteration:
            raise KeyError(f"No matching URI found: '{__key}'")

    def __setitem__(self, __key: str | int | T, __value: T):
        """
        Set attributes of the :py:class:`Item` matching ``__key``
        in this collection to the attributes of ``__value``
        """
        try:
            item = self[__key]
        except KeyError:
            raise KeyError(f"Given index is out of range: {__key}")

        if type(__value) is not type(item):  # only merge attributes if matching types
            raise ValueError("Trying to set on mismatched item types")

        for __key, __value in __value.__dict__.items():  # merge attributes
            setattr(item, __key, deepcopy(__value))

    def __delitem__(self, __key: str | int | T):
        self.remove(__key)


# noinspection PyShadowingNames
class BasicCollection[T: Item](ItemCollection[T]):
    """
    A basic implementation of ItemCollection for storing ``items`` with a given ``name``.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param name: The name of this collection.
    :param items: The items in this collection
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on items.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    """
    @property
    def name(self):
        """The name of this collection"""
        return self._name

    @property
    def items(self) -> list[T]:
        return self._items

    def __init__(self, name: str, items: Collection[T], remote_wrangler: RemoteDataWrangler = None):
        super().__init__(remote_wrangler=remote_wrangler)
        self._name = name
        self._items = to_collection(items, list)

    def as_dict(self):
        return {"name": self.name, "items": self.items}


class Playlist[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """A playlist of items and some of their derived properties/objects."""

    @property
    @abstractmethod
    def name(self):
        """The name of this playlist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str | None:
        """Description of this playlist"""
        raise NotImplementedError

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    @abstractmethod
    def tracks(self):
        """The tracks in this playlist"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks in this playlist"""
        return len(self)

    @property
    @abstractmethod
    def image_links(self) -> dict[str, str]:
        """The images associated with this playlist in the form ``{image name: image link}``"""
        raise NotImplementedError

    @property
    def has_image(self) -> bool:
        """Does this playlist have an image"""
        return len(self.image_links) > 0

    @property
    def length(self) -> float | None:
        """Total duration of all tracks in this playlist in seconds"""
        lengths = {track.length for track in self.tracks}
        return sum(lengths) if lengths else None

    @property
    @abstractmethod
    def date_created(self) -> datetime | None:
        """:py:class:`datetime` object representing when the playlist was created"""
        raise NotImplementedError

    @property
    @abstractmethod
    def date_modified(self) -> datetime | None:
        """:py:class:`datetime` object representing when the playlist was last modified"""
        raise NotImplementedError


# noinspection PyShadowingNames
class Library[T: Track](Logger, ItemCollection[T], metaclass=ABCMeta):
    """
    A library of items and playlists

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on items.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    """

    @property
    @abstractmethod
    def name(self):
        """The library name"""
        raise NotImplementedError

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    @abstractmethod
    def tracks(self):
        """The tracks in this library"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks in this library"""
        return len(self)

    @property
    @abstractmethod
    def playlists(self) -> dict[str, Playlist]:
        """The playlists in this library"""
        raise NotImplementedError

    def __init__(self, remote_wrangler: RemoteDataWrangler = None):
        super().__init__(remote_wrangler=remote_wrangler)

    def get_filtered_playlists(
            self,
            include: Container[str] | None = None,
            exclude: Container[str] | None = None,
            **filter_tags: Iterable[Any]
    ) -> dict[str, Playlist]:
        """
        Returns a filtered set of playlists in this library.
        The playlists returned are deep copies of the playlists in the library.

        :param include: An optional list of playlist names to include.
        :param exclude: An optional list of playlist names to exclude.
        :param filter_tags: Provide optional kwargs of the tags and values of items to filter out of every playlist.
            Parse a tag name as a parameter, any item matching the values given for this tag will be filtered out.
            NOTE: Only `string` value types are currently supported.
        :return: Filtered playlists.
        """
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Filtering playlists and tracks from {len(self.playlists)} playlists\n"
            f"\33[0;90m    Filter out tags: {filter_tags} \33[0m"
        )
        max_width = self.get_max_width(self.playlists)
        bar = self.get_progress_bar(iterable=self.playlists.items(), desc="Filtering playlists", unit="playlists")

        filtered: dict[str, Playlist] = {}
        for name, playlist in bar:
            if (include and name not in include) or (exclude and name in exclude):
                continue

            filtered[name] = deepcopy(playlist)
            for item in playlist.items:
                for tag, filter_vals in filter_tags.items():
                    item_val = item[tag]
                    if not isinstance(item_val, str):
                        continue

                    if any(v.strip().casefold() in item_val.strip().casefold() for v in filter_vals):
                        filtered[name].remove(item)
                        break

            self.logger.debug(
                f"{self.align_and_truncate(name, max_width=max_width)} | "
                f"Filtered out {len(playlist) - len(filtered[name]):>3} items"
            )

        self.print_line()
        return filtered

    @abstractmethod
    def merge_playlists(self, playlists: Self | Collection[Playlist] | Mapping[Any, Playlist]) -> None:
        """Merge playlists from given list/map/library to this library"""
        # TODO: merge playlists adding/removing tracks as needed.
        #  Most likely will need to implement some method on playlist class too
        raise NotImplementedError


class Folder[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """
    A folder of items and some of their derived properties/objects

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    @property
    @abstractmethod
    def name(self):
        """The folder name"""
        raise NotImplementedError

    @property
    def folder(self) -> str:
        """The folder name"""
        return self.name

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    @abstractmethod
    def tracks(self):
        """The tracks in this folder"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this folder"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str]:
        """List of albums ordered by frequency of appearance on the tracks in this folder"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks in this folder"""
        return len(self)

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks in this folder"""
        raise NotImplementedError

    @property
    @abstractmethod
    def compilation(self) -> bool:
        """Is this folder a compilation"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all tracks in this folder"""
        raise NotImplementedError


class Album[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """
    An album of items and some of their derived properties/objects.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The album name"""
        raise NotImplementedError

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    def album(self) -> str:
        """The album name"""
        return self.name

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks on this album"""
        raise NotImplementedError

    @property
    def artist(self) -> str:
        """Joined string representation of all artists on this album ordered by frequency of appearance"""
        return self.tag_sep.join(self.artists)

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks on this album"""
        raise NotImplementedError

    @property
    @abstractmethod
    def album_artist(self) -> str | None:
        """The album artist for this album"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks on this album"""
        return len(self)

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks on this album"""
        raise NotImplementedError

    @property
    @abstractmethod
    def year(self) -> int | None:
        """The year this album was released"""
        raise NotImplementedError

    @property
    def disc_total(self) -> int | None:
        """The highest value of disc number on this album"""
        disc_numbers = {track.disc_number for track in self.tracks if track.disc_number}
        return max(disc_numbers) if disc_numbers else None

    @property
    @abstractmethod
    def compilation(self) -> bool:
        """Is this album a compilation"""
        raise NotImplementedError

    @property
    @abstractmethod
    def image_links(self) -> dict[str, str]:
        """The images associated with this album in the form ``{image name: image link}``"""
        raise NotImplementedError

    @property
    def has_image(self) -> bool:
        """Does this album have an image"""
        return len(self.image_links) > 0

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all tracks on this album in seconds"""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> float | None:
        """Rating of this album"""
        raise NotImplementedError


class Artist[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """
    An artist of items and some of their derived properties/objects

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    @property
    @abstractmethod
    def name(self):
        """The artist name"""
        raise NotImplementedError

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    def artist(self) -> str:
        """The artist name"""
        return self.name

    @property
    @abstractmethod
    def tracks(self) -> list[Track]:
        """The tracks by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of other artists ordered by frequency of appearance on the tracks by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str]:
        """List of albums ordered by frequency of appearance on the tracks by this artist"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks by this artist"""
        return len(self)

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all tracks by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> float | None:
        """Rating of this artist"""
        raise NotImplementedError


class Genre[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """
    A genre of items and some of their derived properties/objects

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    @property
    @abstractmethod
    def name(self):
        """The genre"""
        raise NotImplementedError

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    def genre(self) -> str:
        """The genre"""
        return self.name

    @property
    @abstractmethod
    def tracks(self):
        """The tracks for this genre"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks for this genre"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str]:
        """List of albums ordered by frequency of appearance on the tracks for this genre"""
        raise NotImplementedError

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks for this genre"""
        raise NotImplementedError
