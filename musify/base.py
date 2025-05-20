"""
The fundamental core classes for the entire package.
"""
from __future__ import annotations

from abc import ABCMeta
from dataclasses import dataclass


@dataclass(frozen=True)
class Result(metaclass=ABCMeta):
    """Stores the results of an operation"""
    pass
