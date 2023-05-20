from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping, Collection, Self, Any

from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName
from syncify.utils import UnionList


class Base:
    _list_sep = "; "

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


@dataclass(repr=False, eq=False, unsafe_hash=False, frozen=False)
class Item(Base, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing an item."""

    @property
    @abstractmethod
    def uri(self) -> Optional[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def has_uri(self) -> Optional[bool]:
        raise NotImplementedError

    def merge(self, item: Self, tags: UnionList[TagName] = TagName.ALL):
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
    # metadata/tags
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    track_total: Optional[int] = None
    genres: Optional[Collection[str]] = None
    year: Optional[int] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    disc_number: Optional[int] = None
    disc_total: Optional[int] = None
    compilation: Optional[bool] = None
    comments: Optional[List[str]] = None

    # images
    image_links: Optional[MutableMapping[str, str]] = None
    has_image: bool = False

    # properties
    length: Optional[float] = None
    rating: Optional[float] = None


class TrackProperties:
    date_added: Optional[datetime] = None
    last_played: Optional[datetime] = None
    play_count: Optional[int] = None
