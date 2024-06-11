"""
The fundamental core classes for the entire package.
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any

from musify.field import TagField
from musify.printer import AttributePrinter


@dataclass(frozen=True)
class Result(metaclass=ABCMeta):
    """Stores the results of an operation"""
    pass


###########################################################################
## Core item/object types
###########################################################################
class MusifyObject(AttributePrinter, metaclass=ABCMeta):
    """Generic base class for any nameable and taggable object."""

    __slots__ = ("_clean_tags",)

    #: When representing a list of tags as a string, use this value as the separator.
    tag_sep: str = "; "

    @property
    @abstractmethod
    def name(self) -> str:
        """A name for this object"""
        raise NotImplementedError

    @property
    def clean_tags(self) -> dict[TagField, Any]:
        """A map of tags that have been cleaned to use when matching/searching"""
        return self._clean_tags

    def __init__(self):
        self._clean_tags: dict[TagField, Any] = {}

    def __lt__(self, other: MusifyObject):
        return self.name < other.name

    def __gt__(self, other: MusifyObject):
        return self.name > other.name


class MusifyItem(MusifyObject, metaclass=ABCMeta):
    """Generic class for storing an item."""

    __slots__ = ()

    @property
    @abstractmethod
    def uri(self) -> str | None:
        """URI (Uniform Resource Indicator) is the unique identifier for this item."""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_uri(self) -> bool | None:
        """Does this track have a valid associated URI. When None, answer is unknown."""
        raise NotImplementedError

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError

    def __eq__(self, item: MusifyItem):
        """URI attributes equal if both have a URI, names equal otherwise"""
        if self.has_uri and item.has_uri:
            return self.uri == item.uri
        return self.name == item.name

    def __ne__(self, item: MusifyItem):
        return not self.__eq__(item)

    def __getitem__(self, key: str) -> Any:
        """Get the value of a given attribute key"""
        return getattr(self, key)


# noinspection PyPropertyDefinition
class MusifyItemSettable(MusifyItem, metaclass=ABCMeta):
    """Generic class for storing an item that can have select properties modified."""

    __slots__ = ()

    @abstractmethod
    def _uri_getter(self) -> str | None:
        """URI (Uniform Resource Indicator) is the unique identifier for this item."""
        raise NotImplementedError

    @abstractmethod
    def _uri_setter(self, value: str | None):
        """Set both the ``uri`` property and the ``has_uri`` property ."""
        raise NotImplementedError

    uri = property(
        fget=lambda self: self._uri_getter(),
        fset=lambda self, v: self._uri_setter(v),
        doc="URI (Uniform Resource Indicator) is the unique identifier for this item."
    )


class HasLength(metaclass=ABCMeta):
    """Simple protocol for an object which has a length"""

    __slots__ = ()

    @property
    @abstractmethod
    def length(self):
        """Total duration of this object in seconds"""
        raise NotImplementedError
