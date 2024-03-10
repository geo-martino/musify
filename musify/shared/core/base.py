"""
The fundamental core classes for the entire package.
"""

from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Hashable
from typing import Any

from musify.shared.core.enum import TagField
from musify.shared.core.misc import PrettyPrinter
from musify.shared.types import UnitIterable
from musify.shared.utils import to_collection


class Nameable(ABC):
    """Generic base class for any nameable object."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A name for this object"""
        raise NotImplementedError

    def __lt__(self, other: Nameable):
        return self.name < other.name

    def __gt__(self, other: Nameable):
        return self.name > other.name


class Taggable(ABC):
    """Generic base class for any taggable object."""

    __slots__ = ("_clean_tags",)

    #: When representing a list of tags as a string, use this value as the separator.
    tag_sep: str = "; "

    @property
    def clean_tags(self) -> dict[TagField, Any]:
        """A map of tags that have been cleaned to use when matching/searching"""
        return self._clean_tags

    def __init__(self):
        self._clean_tags: dict[TagField, Any] = {}


class NameableTaggableMixin(Nameable, Taggable, metaclass=ABCMeta):
    """Mixin for :py:class:`Nameable` and :py:class:`Taggable`"""
    pass


class AttributePrinter(PrettyPrinter, metaclass=ABCMeta):
    """
    Extends the functionality of a :py:class:`PrettyPrinter`.

    Adds functionality to automatically determine the key attributes that represent child objects
    and uses these for printer representations.
    """

    __attributes_classes__: UnitIterable[type] = ()
    __attributes_ignore__: UnitIterable[str] = ()

    def _get_attributes(self) -> dict[str, Any]:
        """Returns the key attributes of the current instance for pretty printing"""
        def get_settings(kls: type) -> None:
            """Build up classes and exclude keys for getting attributes"""
            if kls != self.__class__ and kls not in classes:
                classes.append(kls)
            if issubclass(kls, AttributePrinter):
                ignore.update(to_collection(kls.__attributes_ignore__))
                for k in to_collection(kls.__attributes_classes__):
                    get_settings(k)

        classes: list[type] = []
        ignore: set[str] = set()
        get_settings(self.__class__)
        classes.insert(1, self.__class__)

        attributes = {}
        for cls in classes:
            attributes |= {
                k: getattr(self, k) for k in cls.__dict__.keys()
                if k not in ignore and isinstance(getattr(cls, k), property)
            }

        return attributes

    def as_dict(self) -> dict[str, Any]:
        return self._get_attributes()


class Item(AttributePrinter, NameableTaggableMixin, Hashable, metaclass=ABCMeta):
    """Generic class for storing an item."""

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
