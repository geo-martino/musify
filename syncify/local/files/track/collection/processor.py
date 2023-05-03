from abc import ABCMeta, abstractmethod
from typing import Any, Mapping, Optional, Self


class TrackProcessor(metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        """
        raise NotImplementedError

    def inherit(self, obj: Self) -> None:
        """Inherit all variables from an instantiated instance of this class"""
        self.__dict__.update(obj.__dict__)
