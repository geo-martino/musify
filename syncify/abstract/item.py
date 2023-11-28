from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Self, Any
from collections.abc import Collection, Mapping, MutableMapping

from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName
from syncify.utils import UnitList


@dataclass
class BaseObject:
    """Generic base class for all local/Spotify item/collections."""
    clean_tags: MutableMapping[str, Any] = None
    _list_sep: str = "; "

    @property
    @abstractmethod
    def name(self) -> str:
        """A name for this object"""
        raise NotImplementedError


@dataclass(repr=False, eq=False)
class Item(BaseObject, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing an item."""

    @property
    @abstractmethod
    def uri(self) -> str | None:
        """The URI associated with this item."""
        raise NotImplementedError

    @uri.setter
    @abstractmethod
    def uri(self, value: str | None) -> None:
        """Should set both the ``uri`` property and the ``has_uri`` property ."""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_uri(self) -> bool | None:
        """Does this item have a valid URI."""
        raise NotImplementedError

    def merge(self, item: Self, tags: UnitList[TagName] = TagName.ALL):
        """Set the tags of this item equal to the given ``item``. Give a list of ``tags`` to limit which are set"""
        tag_names = set(TagName.to_tags(tags))

        for tag in tag_names:  # merge on each tag
            if hasattr(item, tag):
                setattr(self, tag, item[tag])

    def __hash__(self):
        """Uniqueness of an item is its URI + name"""
        return hash((self.uri, self.name))

    def __eq__(self, item):
        """URI attributes equal if at least one item has a URI, names equal otherwise"""
        if self.has_uri or item.has_uri:
            return self.has_uri == item.has_uri and self.uri == item.uri
        else:
            return self.name == item.name

    def __ne__(self, item):
        return not self.__eq__(item)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
        if not hasattr(self, key):
            raise KeyError(f"Given key is not a valid attribute of this item: {key}")
        return setattr(self, key, value)


class Track(Item, metaclass=ABCMeta):
    """Metadata/tags associated with a track."""

    # metadata/tags
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    track_number: int | None = None
    track_total: int | None = None
    genres: Collection[str] | None = None
    year: int | None = None
    bpm: float | None = None
    key: str | None = None
    disc_number: int | None = None
    disc_total: int | None = None
    compilation: bool | None = None
    comments: list[str] | None = None

    # images
    image_links: Mapping[str, str] | None = None
    has_image: bool = False

    # properties
    length: float | None = None
    rating: float | None = None


class TrackProperties:
    """Properties associated with a track."""

    date_added: datetime | None = None
    last_played: datetime | None = None
    play_count: int | None = None
