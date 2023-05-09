from abc import ABCMeta, abstractmethod
from typing import Any, Mapping, Optional, Self, List, Union

from syncify.utils_new.generic import PrettyPrinter


class TrackProcessor(PrettyPrinter, metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        """
        raise NotImplementedError

    def _get_method_name(
            self, value: str, valid: Union[List[str], Mapping[str, str]], prefix: Optional[str] = None
    ) -> str:
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
