from abc import ABCMeta

from syncify.abstract.item import Item
from syncify.local._file import File


class LocalItem(File, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""
    pass
