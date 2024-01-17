"""
Core abstract classes for the :py:mod:`Local` module.
"""

from abc import ABCMeta

from musify.local.file import File
from musify.shared.core.base import Item


class LocalItem(File, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""

    __attributes_classes__ = (File, Item)
