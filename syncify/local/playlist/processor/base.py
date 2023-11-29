from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Iterable
from typing import Any, Self

from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName, Name


class TrackProcessor(PrettyPrinter, metaclass=ABCMeta):
    """Base object for processing tracks in a playlist"""

    @classmethod
    @abstractmethod
    def from_xml(cls, xml: Mapping[str, Any] | None = None) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
        """
        raise NotImplementedError

    def _get_method_name(self, value: str, valid: Iterable[str] | Mapping[str | str], prefix: str | None = None) -> str:
        """
        Find a method that matches the given string from a list of valid methods.

        :param value: The name of the method to search for. This will be automatically sanitised to snake_case.
        :param valid: A list of strings representing the methods to search through.
            May also provide a map of strings to match on a method names to return.
        :param prefix: An optional prefix to append to the sanitised value.
            Also used to remove prefixes from the valid methods when logging an error
        :return: The sanitised value representing the name of the method.
        :raises LookupError: When the method cannot be found in the valid list.
        """
        sanitised = self._camel_to_snake(value, prefix=prefix)

        if sanitised not in valid:
            valid_methods_str = ", ".join([c.replace(prefix, "") if prefix is not None else c for c in valid])
            raise LookupError(
                f"Unrecognised method: '{value}' (sanitised to '{sanitised}') | " 
                f"Valid methods: {valid_methods_str}"
            )

        return sanitised

    @classmethod
    def _get_tag(cls, tag: Name | None = None) -> str:
        return tag.to_tag()[0] if isinstance(tag, TagName) else tag.name.casefold()
