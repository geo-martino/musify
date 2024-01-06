from abc import ABCMeta

from syncify.shared.core.base import Item
from syncify.local.file import File


class LocalItem(File, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""

    def __hash__(self):  # TODO: why doesn't this get inherited correctly from File
        return super().__hash__()
