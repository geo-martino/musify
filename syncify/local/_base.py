from abc import ABCMeta

from syncify.abstract.item import BaseObject, Item
from syncify.local._file import File


class LocalObject(BaseObject, File, metaclass=ABCMeta):
    """Generic base class for locally-stored objects"""
    pass


class LocalItem(LocalObject, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""
    pass
