from abc import ABCMeta

from syncify.abstract.item import BaseObject, Item
from syncify.local.file import File


class LocalObject(BaseObject, File, metaclass=ABCMeta):
    """Generic base class for locally-stored objects"""
    def __init__(self):
        BaseObject.__init__(self)


class LocalItem(LocalObject, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""
    def __init__(self):
        LocalObject.__init__(self)
        Item.__init__(self)
