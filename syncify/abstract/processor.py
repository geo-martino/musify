from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from typing import Any, Self, Callable

from syncify.abstract.misc import PrettyPrinter
from syncify.enums.tags import TagName, Name
from syncify.processors.decorators import dynamicprocessormethod
from syncify.processors.exception import ProcessorLookupError


class Processor(PrettyPrinter, metaclass=ABCMeta):
    """Generic base class for processors"""


class DynamicProcessor(Processor, metaclass=ABCMeta):
    """
    Base class for implementations with :py:function:`dynamicprocessormethod` methods.

    Classes that implement this base class have a ``__processormethods__`` class attribute
    which is a list of strings of all the processor methods this class contains.
    If a :py:function:`dynamicprocessormethod` has alternative method names, these names will be added
    to the class' ``__dict__`` as callable methods which point to the decorated method.

    Optionally, you may also define a ``_processor_method_fmt`` classmethod which
    applies some transformation to all method names.
    The transformed method name is then appended to the class' ``__dict__``.
    The transformation is always applied before extending the class with any given
    alternative method names.

    :ivar __processormethods__: The set of processor methods on this processor and any alternative names for them.
    """

    __processormethods__: frozenset[str] = frozenset()

    @property
    def processor_methods(self) -> frozenset[str]:
        """String representation of the current processor name of this object"""
        return frozenset(self._processor_method_fmt(name) for name in self.__processormethods__)

    def __new__(cls, *args, **kwargs):
        processor_methods = list(cls.__processormethods__)

        for method in cls.__dict__.copy().values():
            if not isinstance(method, dynamicprocessormethod):
                continue

            processor_methods.append(method.__name__)
            transformed_name = cls._processor_method_fmt(method.__name__)
            if transformed_name != method.__name__:
                processor_methods.append(transformed_name)
                setattr(cls, transformed_name, method)

            processor_methods.extend(method.alternative_names)
            for name in method.alternative_names:
                setattr(cls, cls._processor_method_fmt(name), method)

        cls.__processormethods__ = frozenset(processor_methods)
        return super().__new__(cls)

    def __init__(self):
        self._processor_name: str | None = None

    @classmethod
    def _processor_method_fmt(cls, name: str) -> str:
        """A custom formatter to apply to the dynamic processor name"""
        return name

    def _set_processor_name(self, value: str, fail_on_empty: bool = True):
        """Verifies and sets the condition name"""
        if value is None:
            if not fail_on_empty:
                self._processor_name = None
                return
            raise ProcessorLookupError("No condition given")

        name = self._processor_method_fmt(value)
        if name not in self.processor_methods:
            raise ProcessorLookupError(f"'{value}' condition is not valid")

        self._processor_name = name

    @property
    def _processor(self) -> Callable:
        """The callable method of the dynamic processor"""
        return getattr(self, self._processor_name)

    def _process(self, *args, **kwargs) -> Any:
        """Run the dynamic processor"""
        return self._processor(*args, **kwargs)


class ItemProcessor(Processor, metaclass=ABCMeta):
    """Base object for processing tracks in a playlist"""

    @classmethod
    def _get_tag(cls, tag: Name | None = None) -> str:
        """Get the human-friendly tag name as a string of the given tag name enum"""
        return tag.to_tag()[0] if isinstance(tag, TagName) else tag.name.casefold()


class MusicBeeProcessor(ItemProcessor):

    @classmethod
    def _processor_method_fmt(cls, name: str) -> str:
        """A custom formatter to apply to the dynamic processor name"""
        return "_" + cls._camel_to_snake(name).lstrip("_")

    @classmethod
    @abstractmethod
    def from_xml(cls, xml: Mapping[str, Any], **kwargs) -> Self:
        """
        Initialise object from XML playlist data.

        :param xml: The loaded XML object for this playlist.
        """
        raise NotImplementedError

    @abstractmethod
    def to_xml(self, **kwargs) -> Mapping[str, Any]:
        """Export this object's settings to a map ready for export to an XML playlist file."""
        raise NotImplementedError