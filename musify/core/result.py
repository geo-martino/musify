"""
The fundamental core result classes for the entire package.
"""
from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class Result(ABC):
    """Stores the results of an operation"""
    pass
