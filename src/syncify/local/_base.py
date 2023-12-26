from abc import ABCMeta

from syncify.abstract.item import Item
from syncify.local._file import File


class LocalItem(File, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""

    def __hash__(self):  # TODO: why doesn't this get inherited correctly from File
        return super().__hash__()
