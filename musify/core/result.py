"""
The fundamental core result classes for the entire package.
"""
from abc import ABCMeta
from dataclasses import dataclass


@dataclass(frozen=True)
class Result(metaclass=ABCMeta):
    """Stores the results of an operation"""
    pass
