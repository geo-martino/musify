"""
The core implementations of :py:class:`Item` and :py:class:`ItemCollection` classes.
"""

from __future__ import annotations

import datetime
import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Collection, Mapping
from copy import deepcopy
from typing import Any, Self

from musify.processors.base import Filter
from musify.processors.filter import FilterDefinedList
from musify.shared.core.base import Item
from musify.shared.core.collection import ItemCollection
from musify.shared.exception import MusifyKeyError, MusifyTypeError
from musify.shared.logger import MusifyLogger
from musify.shared.utils import to_collection, align_string, get_max_width


class Track(Item, metaclass=ABCMeta):
    """Represents a track including its metadata/tags/properties."""

    __attributes_ignore__ = "name"

    @property
    def name(self) -> str:
        """This track's title"""
        return self.title

    @property
    @abstractmethod
    def title(self) -> str | None:
        """This track's title"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artist(self) -> str | None:
        """Joined string representation of all artists featured on this track"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str | Artist]:
        """List of all artists featured on this track."""
        raise NotImplementedError

    @property
    @abstractmethod
    def album(self) -> str | None:
        """The album this track is featured on"""
        raise NotImplementedError

    @property
    @abstractmethod
    def album_artist(self) -> str | None:
        """The artist of the album this track is featured on"""
        raise NotImplementedError

    @property
    @abstractmethod
    def track_number(self) -> int | None:
        """The position this track has on the album it is featured on"""
        raise NotImplementedError

    @property
    @abstractmethod
    def track_total(self) -> int | None:
        """The track number of tracks on the album this track is featured on"""
        raise NotImplementedError

    @property
    @abstractmethod
    def genres(self) -> list[str] | None:
        """List of genres associated with this track"""
        raise NotImplementedError

    @property
    def date(self) -> datetime.date | None:
        """A :py:class:`date` object representing the release date of this track"""
        if self.year and self.month and self.day:
            return datetime.date(self.year, self.month, self.day)

    @property
    @abstractmethod
    def year(self) -> int | None:
        """The year this track was released"""
        raise NotImplementedError

    @property
    @abstractmethod
    def month(self) -> int | None:
        """The month this track was released"""
        raise NotImplementedError

    @property
    @abstractmethod
    def day(self) -> int | None:
        """The day this track was released"""
        raise NotImplementedError

    @property
    @abstractmethod
    def bpm(self) -> float | None:
        """The tempo of this track"""
        raise NotImplementedError

    @property
    @abstractmethod
    def key(self) -> str | None:
        """The key of this track in alphabetical musical notation format"""
        raise NotImplementedError

    @property
    @abstractmethod
    def disc_number(self) -> int | None:
        """The number of the disc from the album this track is featured on"""
        raise NotImplementedError

    @property
    @abstractmethod
    def disc_total(self) -> int | None:
        """The total number the discs from the album this track is featured on"""
        raise NotImplementedError

    @property
    @abstractmethod
    def compilation(self) -> bool | None:
        """Is the album this track is featured on a compilation"""
        raise NotImplementedError

    @property
    @abstractmethod
    def comments(self) -> list[str] | None:
        """Comments associated with this track set by the user"""
        raise NotImplementedError

    @property
    @abstractmethod
    def image_links(self) -> dict[str, str]:
        """
        The images associated with the album this track is featured on in the form ``{<image name/type>: <image link>}``
        """
        raise NotImplementedError

    @property
    def has_image(self) -> bool:
        """Does the album this track is associated with have an image"""
        return len(self.image_links) > 0

    @property
    @abstractmethod
    def length(self) -> float:
        """Total duration of this track in seconds"""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> float | None:
        """The rating for this track"""
        raise NotImplementedError


class BasicCollection[T: Item](ItemCollection[T]):
    """
    A basic implementation of ItemCollection for storing ``items`` with a given ``name``.

    :param name: The name of this collection.
    :param items: The items in this collection
    """

    __slots__ = ("_name", "_items")

    @staticmethod
    def _validate_item_type(items: Any | Iterable[Any]) -> bool:
        if isinstance(items, Iterable):
            return all(isinstance(item, Item) for item in items)
        return isinstance(items, Item)

    @property
    def name(self):
        """The name of this collection"""
        return self._name

    @property
    def items(self) -> list[T]:
        return self._items

    def __init__(self, name: str, items: Collection[T]):
        super().__init__()
        self._name = name
        self._items = to_collection(items, list)

    def __getitem__(self, __key: str | int | slice | Item) -> T | list[T] | list[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI.
        If an item is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri:
                raise MusifyKeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri
        else:  # assume the string is a name
            try:
                return next(item for item in self.items if item.name == __key)
            except StopIteration:
                raise MusifyKeyError(f"No matching item found for name: '{__key}'")

        try:  # string is a URI
            return next(item for item in self.items if item.uri == __key)
        except StopIteration:
            raise MusifyKeyError(f"No matching item found for URI: '{__key}'")


class Playlist[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """A playlist of items and their derived properties/objects."""

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = "items"

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
    def tracks(self) -> list[T]:
        """The tracks in this playlist"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks in this playlist"""
        return len(self)

    @property
    @abstractmethod
    def image_links(self) -> dict[str, str]:
        """The images associated with this playlist in the form ``{<image name/type>: <image link>}``"""
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
    def date_created(self) -> datetime.datetime | None:
        """:py:class:`datetime.datetime` object representing when the playlist was created"""
        raise NotImplementedError

    @property
    @abstractmethod
    def date_modified(self) -> datetime.datetime | None:
        """:py:class:`datetime.datetime` object representing when the playlist was last modified"""
        raise NotImplementedError

    @abstractmethod
    def merge(self, playlist: Playlist[T]) -> None:
        """
        **WARNING: NOT IMPLEMENTED YET**
        Merge tracks in this playlist with another playlist synchronising tracks between the two.
        Only modifies this playlist.
        """
        # TODO: merge playlists adding/removing tracks as needed.
        raise NotImplementedError

    # noinspection PyTypeChecker
    def __or__(self, other: Playlist[T]) -> Self:
        if not isinstance(other, self.__class__):
            raise MusifyTypeError(
                f"Incorrect item given. Cannot merge with {other.__class__.__name__} "
                f"as it is not a {self.__class__.__name__}"
            )
        raise NotImplementedError

    # noinspection PyTypeChecker
    def __ior__(self, other: Playlist[T]) -> Self:
        if not isinstance(other, self.__class__):
            raise MusifyTypeError(
                f"Incorrect item given. Cannot merge with {other.__class__.__name__} "
                f"as it is not a {self.__class__.__name__}"
            )
        raise NotImplementedError


class Library[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """A library of items and playlists and other object types."""

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = "items"

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
    def tracks(self) -> list[T]:
        """The tracks in this library"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks in this library"""
        return len(self)

    @property
    def tracks_in_playlists(self) -> set[T]:
        """All unique tracks from all playlists in this library"""
        return set(track for pl in self.playlists.values() for track in pl)

    @property
    @abstractmethod
    def playlists(self) -> dict[str, Playlist[T]]:
        """The playlists in this library"""
        raise NotImplementedError

    def __init__(self):
        super().__init__()

        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

    def get_filtered_playlists(
            self, playlist_filter: Collection[str] | Filter[str] = (), **tag_filter: dict[str, tuple[str, ...]]
    ) -> dict[str, Playlist[T]]:
        """
        Returns a filtered set of playlists in this library.
        The playlists returned are deep copies of the playlists in the library.

        :param playlist_filter: An optional :py:class:`Filter` to apply or collection of playlist names.
            Playlist names will be passed to this filter to limit which playlists are processed.
        :param tag_filter: Provide optional kwargs of the tags and values of items to filter out of every playlist.
            Parse a tag name as a parameter, any item matching the values given for this tag will be filtered out.
            NOTE: Only `string` value types are currently supported.
        :return: Filtered playlists.
        """
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Filtering playlists and tracks from {len(self.playlists)} playlists\n"
            f"\33[0;90m    Filter out tags: {tag_filter} \33[0m"
        )

        if not isinstance(playlist_filter, Filter):
            playlist_filter = FilterDefinedList(playlist_filter)
        pl_filtered = [
            pl for name, pl in self.playlists.items() if not playlist_filter or name in playlist_filter(self.playlists)
        ]

        max_width = get_max_width(self.playlists)
        filtered: dict[str, Playlist[T]] = {}
        for pl in self.logger.get_progress_bar(iterable=pl_filtered, desc="Filtering playlists", unit="playlists"):
            filtered[pl.name] = deepcopy(pl)
            for track in pl.tracks:
                for tag, values in tag_filter.items():
                    item_val = track[tag]
                    if not isinstance(item_val, str):
                        continue

                    if any(v.strip().casefold() in item_val.strip().casefold() for v in values):
                        filtered[pl.name].remove(track)
                        break

            self.logger.debug(
                f"{align_string(pl.name, max_width=max_width)} | "
                f"Filtered out {len(pl) - len(filtered[pl.name]):>3} items"
            )

        self.logger.print()
        return filtered

    @abstractmethod
    def load(self):
        """Implementations of this function should load all data for this library and log results."""
        raise NotImplementedError

    @abstractmethod
    def load_tracks(self) -> None:
        """
        Implementations of this function should load all tracks for this library
        and store them within the library object to be retrieved with property ``tracks``.
        """
        raise NotImplementedError

    @abstractmethod
    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        raise NotImplementedError

    @abstractmethod
    def load_playlists(self) -> None:
        """
        Implementations of this function should load all playlists for this library
        and store them within the library object to be retrieved with property ``playlists``.
        """
        raise NotImplementedError

    @abstractmethod
    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        raise NotImplementedError

    @abstractmethod
    def merge_playlists(self, playlists: Library[T] | Collection[Playlist[T]] | Mapping[Any, Playlist[T]]) -> None:
        """
        **WARNING: NOT IMPLEMENTED YET**
        Merge playlists from given list/map/library to this library
        """
        # TODO: merge playlists adding/removing tracks as needed.
        #  Most likely will need to implement some method on playlist class too
        raise NotImplementedError


class Folder[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """
    A folder of items and their derived properties/objects
    """

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = ("name", "items")

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
    """An album of items and their derived properties/objects."""

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = ("name", "items")

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
    def tracks(self) -> list[T]:
        """The tracks on this album"""
        raise NotImplementedError

    @property
    def artist(self) -> str:
        """Joined string representation of all artists on this album ordered by frequency of appearance"""
        return self.tag_sep.join(self.artists)

    @property
    @abstractmethod
    def artists(self) -> list[str | Artist]:
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
    def date(self) -> datetime.date | None:
        """A :py:class:`date` object representing the release date of this album"""
        if self.year and self.month and self.day:
            return datetime.date(self.year, self.month, self.day)

    @property
    @abstractmethod
    def year(self) -> int | None:
        """The year this album was released"""
        raise NotImplementedError

    @property
    @abstractmethod
    def month(self) -> int | None:
        """The month this album was released"""
        raise NotImplementedError

    @property
    @abstractmethod
    def day(self) -> int | None:
        """The day this album was released"""
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
        """The images associated with this album in the form ``{<image name/type>: <image link>}``"""
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
    """An artist of items and their derived properties/objects."""

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = ("name", "items")

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
    def tracks(self) -> list[T]:
        """The tracks by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def artists(self) -> list[str]:
        """List of other artists ordered by frequency of appearance on the albums by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def albums(self) -> list[str | Album]:
        """List of albums ordered by frequency of appearance on the tracks by this artist"""
        raise NotImplementedError

    @property
    def track_total(self) -> int:
        """The total number of tracks by this artist"""
        return len(self)

    @property
    @abstractmethod
    def genres(self) -> list[str]:
        """List of genres for this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float | None:
        """Total duration of all tracks by this artist"""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> int | None:
        """The popularity of this artist"""
        raise NotImplementedError


class Genre[T: Track](ItemCollection[T], metaclass=ABCMeta):
    """A genre of items and their derived properties/objects."""

    __attributes_classes__ = ItemCollection
    __attributes_ignore__ = ("name", "items")

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
    def tracks(self) -> list[T]:
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
