from abc import ABCMeta, abstractmethod
from collections.abc import Hashable
from datetime import datetime
from typing import Self, Any

from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName
from syncify.utils import UnitIterable


class BaseObject:
    """Generic base class for all local/Spotify item/collections."""
    _tag_sep: str = "; "

    @property
    @abstractmethod
    def name(self) -> str:
        """A name for this object"""
        raise NotImplementedError

    @property
    def clean_tags(self) -> dict[str, Any]:
        """A map of tags that have been cleaned to use when matching/searching"""
        return self._clean_tags

    def __init__(self):
        self._clean_tags: dict[str, Any] = {}


class Item(BaseObject, PrettyPrinter, Hashable, metaclass=ABCMeta):
    """Generic class for storing an item."""

    @property
    @abstractmethod
    def uri(self) -> str | None:
        """URI (Uniform Resource Indicator) is the unique identifier for this item."""
        raise NotImplementedError

    @uri.setter
    @abstractmethod
    def uri(self, value: str | None) -> None:
        """Should set both the ``uri`` property and the ``has_uri`` property ."""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_uri(self) -> bool | None:
        """Does this track have a valid associated URI. When None, answer is unknown."""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float:
        """Total duration of this item in seconds"""
        raise NotImplementedError

    def merge(self, item: Self, tags: UnitIterable[TagName] = TagName.ALL) -> None:
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

    @property
    @abstractmethod
    def name(self) -> str:
        """This track's title"""
        raise NotImplementedError

    @property
    @abstractmethod
    def length(self) -> float:
        """Total duration of this track in seconds"""
        raise NotImplementedError

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
    @abstractmethod
    def year(self) -> int | None:
        """The year this track was released"""
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
        """The images associated with the album this track is featured on in the form ``{image name: image link}``"""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_image(self) -> bool:
        """Does the album this track is associated with have an image"""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> float | None:
        """The popularity of this track on Spotify"""
        raise NotImplementedError


class TrackProperties:
    """Properties associated with a track."""

    @property
    @abstractmethod
    def date_added(self) -> datetime | None:
        """The timestamp for when this track was added to the associated collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def last_played(self) -> datetime | None:
        """The timestamp when this track was last played"""
        raise NotImplementedError

    @property
    @abstractmethod
    def play_count(self) -> int | None:
        """The total number of times this track has been played"""
        raise NotImplementedError
