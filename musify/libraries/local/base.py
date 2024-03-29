"""
Core abstract classes for the :py:mod:`Local` module.
"""
from abc import ABCMeta

from musify.core.base import MusifyItem
from musify.file.base import File


class LocalItem(File, MusifyItem, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""

    __attributes_classes__ = (File, MusifyItem)
