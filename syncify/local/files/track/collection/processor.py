from abc import ABCMeta, abstractmethod
from enum import IntEnum
from typing import Any, Mapping, Optional, Self, Type

from syncify.local.files.utils.exception import EnumNotFoundError
from syncify.utils_new.generic import PP


class Mode(IntEnum):

    @classmethod
    def from_name(cls, name: str) -> Self:
        """
        Returns the first enum that matches the given name

        :exception EnumNotFoundError: If a corresponding enum cannot be found.
        """
        for enum in cls:
            if name.upper() == enum.name:
                return enum
        raise EnumNotFoundError(name)


class TrackProcessor(PP, metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        """
        raise NotImplementedError

    def inherit(self, obj: Type[Self]) -> None:
        """Inherit all variables from an instantiated instance of this class"""
        self.__dict__.update(obj.__dict__)
