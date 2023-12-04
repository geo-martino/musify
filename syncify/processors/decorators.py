from collections.abc import Callable, Iterable
from functools import partial, update_wrapper
from typing import Optional


class dynamicprocessormethod:
    """
    Decorator for methods on a class decorated with the :py:func:`processor` decorator

    This assigns the method a processor method which can be dynamically called by the processor class.
    Optionally, provide a list of alternative names from which this processor method can also be called.
    """
    def __new__(cls, *args, **kwargs):
        func: Optional[Callable] = next((a for a in args if callable(a)), None)

        self = partial(cls, *args) if func is None else super().__new__(cls)
        return update_wrapper(self, func)

    def __init__(self, *args: Optional[Callable] | Iterable[str]):
        self.func = next((a for a in args if callable(a)), None)
        self.alternative_names = tuple(a for a in args if isinstance(a, str))

    def __get__(self, instance, owner):
        self.instance_ = instance
        return self.__call__

    def __call__(self, *args, **kwargs):
        return self.func(self.instance_, *args, **kwargs)
