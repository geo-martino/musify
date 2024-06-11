"""
Just the core abstract class for the :py:mod:`Remote` module.
Placed here separately to avoid circular import logic issues.
"""
from abc import ABCMeta, abstractmethod
from typing import Any

from musify.base import MusifyObject
from musify.libraries.remote.core.enum import RemoteObjectType


class RemoteResponse(MusifyObject, metaclass=ABCMeta):

    __slots__ = ()

    @property
    @abstractmethod
    def response(self) -> dict[str, Any]:
        """The API response for this object"""
        raise NotImplementedError

    @property
    @abstractmethod
    def id(self) -> str:
        """The ID of this item/collection."""
        raise NotImplementedError

    # noinspection PyPropertyDefinition,PyMethodParameters
    @property
    @abstractmethod
    def kind(cls) -> RemoteObjectType:
        """The type of remote object this class represents"""
        raise NotImplementedError

    @abstractmethod
    def refresh(self, skip_checks: bool = False) -> None:
        """
        Refresh this object by updating from the stored API response.
        Useful for updating stored variables after making changes to the stored API response manually.
        """
        raise NotImplementedError
