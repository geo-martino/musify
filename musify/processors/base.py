"""
Base classes for all processors in this module. Also contains decorators for use in implementations.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Callable, Collection, Iterable
from functools import partial, update_wrapper
from typing import Any, Self, Optional

from musify.processors.exception import ProcessorLookupError
from musify.shared.core.misc import PrettyPrinter


class Processor:
    """Generic base class for processors"""


# noinspection PyPep8Naming,SpellCheckingInspection
class dynamicprocessormethod:
    """
    Decorator for methods on a class decorated with the :py:func:`processor` decorator

    This assigns the method a processor method which can be dynamically called by the processor class.
    Optionally, provide a list of alternative names from which this processor method can also be called.
    """
    def __new__(cls, *args, **__):
        func: Optional[Callable] = next((a for a in args if callable(a)), None)
        self = partial(cls, *args) if func is None else super().__new__(cls)
        return update_wrapper(self, func)

    def __init__(self, *args: str | Callable):
        self.func = next((a for a in args if callable(a)), None)
        self.alternative_names = tuple(a for a in args if isinstance(a, str))
        self.instance_ = None

    def __get__(self, instance, owner):
        self.instance_ = instance
        return self.__call__

    def __call__(self, *args, **kwargs):
        return self.func(self.instance_, *args, **kwargs) if self.instance_ else self.func(*args, **kwargs)


# noinspection SpellCheckingInspection
class DynamicProcessor(Processor, metaclass=ABCMeta):
    """
    Base class for implementations with :py:func:`dynamicprocessormethod` methods.

    Classes that implement this base class have a ``__processormethods__`` class attribute
    which is a list of strings of all the processor methods this class contains.
    If a :py:func:`dynamicprocessormethod` has alternative method names, these names will be added
    to the class' ``__dict__`` as callable methods which point to the decorated method.

    Optionally, you may also define a ``_processor_method_fmt`` class method which
    applies some transformation to all method names.
    The transformed method name is then appended to the class' ``__dict__``.
    The transformation is always applied before extending the class with any given
    alternative method names.
    """

    __slots__ = ("_processor_name",)

    #: The set of processor methods on this processor and any alternative names for them.
    __processormethods__: frozenset[str] = frozenset()

    @property
    def processor_methods(self) -> frozenset[str]:
        """String representation of the current processor name of this object"""
        return frozenset(self._processor_method_fmt(name) for name in self.__processormethods__)

    def __new__(cls, *_, **__):
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

    def _set_processor_name(self, value: str | None, fail_on_empty: bool = True):
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
    def _processor_method(self) -> Callable:
        """The callable method of the dynamic processor"""
        return getattr(self, self._processor_name)

    def __call__(self, *args, **kwargs) -> Any:
        """Run the dynamic processor"""
        return self._processor_method(*args, **kwargs)


class ItemProcessor(Processor, PrettyPrinter, metaclass=ABCMeta):
    """Base object for processing :py:class:`Item` objects"""


class MusicBeeProcessor(ItemProcessor):
    """Base object for processing :py:class:`Item` objects on MusicBee settings"""

    @classmethod
    def _processor_method_fmt(cls, name: str) -> str:
        """A custom formatter to apply to the dynamic processor name"""
        return "_" + cls._pascal_to_snake(name)

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


class Filter[T](Processor, PrettyPrinter, metaclass=ABCMeta):
    """Base class for filtering down values based on some settings"""

    __slots__ = ("_transform",)

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Does this filter have valid settings and can process values"""
        raise NotImplementedError

    @abstractmethod
    def process(self, values: Collection[T], *args, **kwargs) -> Collection[T]:
        """Apply this filter's settings to the given values"""
        raise NotImplementedError

    @property
    def transform(self) -> Callable[[Any], Any]:
        """
        Transform the input ``value`` to the value that should be used when comparing against this filter's settings
        Simply returns the given ``value`` at baseline unless overriden.
        """
        return self._transform

    @transform.setter
    def transform(self, transformer: Callable[[Any], Any]):
        self._transform = transformer

    def __init__(self):
        self._transform = lambda x: x

    def __call__(self, *args, **kwargs) -> Collection[T]:
        return self.process(*args, **kwargs)

    def __bool__(self):
        return self.ready


class FilterComposite[T](Filter[T], Collection[Filter], metaclass=ABCMeta):
    """Composite filter which filters based on many :py:class:`Filter` objects"""

    __slots__ = ("filters",)

    @property
    def ready(self):
        return any(filter_.ready for filter_ in self.filters)

    @property
    def transform(self) -> Callable[[Any], Any]:
        return lambda _: None

    @transform.setter
    def transform(self, transformer: Callable[[Any], Any]):
        for filter_ in self.filters:
            filter_.transform = transformer

    def __init__(self, *filters: Filter[T], **__):
        super().__init__()

        #: The filters to use when processing
        self.filters = filters

    def __iter__(self):
        def flat_filter_list(filter_: Filter | Collection[Filter]) -> Iterable[Filter]:
            """
            Get flat list of all :py:class:`Filter` objects in the given Filter,
            flattening out any :py:class:`FilterComposite` objects
            """
            if isinstance(filter_, FilterComposite):
                return iter(filter_)
            return [filter_]
        return (f for filter_ in self.filters for f in flat_filter_list(filter_))

    def __len__(self):
        return len(self.filters)

    def __contains__(self, item: Any):
        return item in self.filters
