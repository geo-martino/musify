"""
Core abstract classes for the :py:mod:`Local` module.
"""
from abc import ABC

from musify.core.base import MusifyItemSettable
from musify.file.base import File


class LocalItem(File, MusifyItemSettable, ABC):
    """Generic base class for locally-stored items"""

    __slots__ = ()
    __attributes_classes__ = (File, MusifyItemSettable)
