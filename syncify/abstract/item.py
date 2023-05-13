from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, MutableMapping, Collection

from syncify.abstract.misc import PrettyPrinter


class Base:
    list_sep = "; "

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


@dataclass(repr=False, eq=False, unsafe_hash=False, frozen=False)
class Item(Base, PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing an item."""

    uri: Optional[str] = None
    has_uri: Optional[bool] = None

    def __hash__(self):
        return hash(self.uri) if self.has_uri else hash(self.name)

    def __eq__(self, item):
        if self.has_uri or item.has_uri:
            return self.has_uri == item.has_uri and self.uri == item.uri
        else:
            return self.name == item.name

    def __ne__(self, item):
        return not self.__eq__(item)


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

    # file properties
    size: Optional[int] = None
    length: Optional[float] = None
    date_modified: Optional[datetime] = None

    # library properties
    date_added: Optional[datetime] = None
    last_played: Optional[datetime] = None
    play_count: Optional[int] = None
    rating: Optional[float] = None
