"""
Core abstract classes for the :py:mod:`Local` module.
"""
from abc import ABCMeta

from musify.model._base import MusifyItemSettable
from musify.model.properties.file import File


class LocalItem(File, MusifyItemSettable, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""

    __slots__ = ()
    __attributes_classes__ = (File, MusifyItemSettable)
