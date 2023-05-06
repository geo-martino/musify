import re
from abc import ABCMeta, abstractmethod
from enum import IntEnum
from typing import Any, Mapping, Optional, Self, List, Union

from syncify.local.files.utils.exception import EnumNotFoundError
from syncify.utils_new.generic import PrettyPrinter


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


class TrackProcessor(PrettyPrinter, metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        """
        raise NotImplementedError

    def _get_method_name(self, value: str, valid: Union[List[str], Mapping[str, str]], prefix: Optional[str] = None) -> str:
        """
        Find a method that matches the given string from a list of valid methods.

        :param value: The name of the method to search for. This will be automatically sanitised to snake_case.
        :param valid: A list of strings representing the methods to search through.
            May also provide a map of strings to match on a method names to return.
        :param prefix: An optional prefix to append to the sanitised value.
            Also used to remove prefixes from the valid methods when logging an error
        :return: The sanitised value representing the name of the method.
        :exception ValueError: When the method cannot be found in the valid list.
        """
        sanitised = self._camel_to_snake(value, prefix=prefix)

        if sanitised not in valid:
            valid_methods_str = ", ".join([c.replace(prefix, "") if prefix is not None else c for c in valid])
            raise ValueError(
                f"Unrecognised method: '{value}' (sanitised to '{sanitised}') | " 
                f"Valid methods: {valid_methods_str}"
            )

        return sanitised

    @staticmethod
    def _camel_to_snake(value: str, prefix: Optional[str] = None) -> str:
        """Convert snake_case to CamelCase. Optionally, add a given prefix"""
        value = re.sub('([A-Z])', lambda m: f"_{m.group(1).lower()}", value.strip("_ "))
        value = re.sub(r"[_ ]+", "_", value).strip("_ ")
        if prefix is not None:
            value = f"{prefix}_{value}"
        return value.lower()

    @staticmethod
    def _snake_to_camel(value: str, prefix: Optional[str] = None) -> str:
        """Convert snake_case to CamelCase. Optionally, remove a given prefix"""
        if prefix is not None:
            value = re.sub(f'^{prefix}', "", value)
        return re.sub('_(.)', lambda m: m.group(1).upper(), value.strip())
