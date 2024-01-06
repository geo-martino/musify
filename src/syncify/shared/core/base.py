from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Hashable
from typing import Any

from syncify.shared.core.enums import TagField
from syncify.shared.core.misc import PrettyPrinter


class NamedObject(ABC):
    """
    Generic base class for all local/remote item/collections.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    __slots__ = ("_clean_tags",)

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

    def __lt__(self, other: NamedObject):
        return self.name < other.name

    def __gt__(self, other: NamedObject):
        return self.name > other.name


class NamedObjectPrinter(NamedObject, PrettyPrinter, metaclass=ABCMeta):
    pass


class Item(NamedObjectPrinter, Hashable, metaclass=ABCMeta):
    """
    Generic class for storing an item.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    @property
    @abstractmethod
    def uri(self) -> str | None:
        """URI (Uniform Resource Indicator) is the unique identifier for this item."""
        raise NotImplementedError

    @uri.setter
    @abstractmethod
    def uri(self, value: str | None) -> None:
        """Set both the ``uri`` property and the ``has_uri`` property ."""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_uri(self) -> bool | None:
        """Does this track have a valid associated URI. When None, answer is unknown."""
        raise NotImplementedError

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError

    def __eq__(self, item: Item):
        """URI attributes equal if both have a URI, names equal otherwise"""
        if self.has_uri and item.has_uri:
            return self.uri == item.uri
        return self.name == item.name

    def __ne__(self, item: Item):
        return not self.__eq__(item)

    def __getitem__(self, key: str) -> Any:
        """Get the value of a given attribute key"""
        return getattr(self, key)
