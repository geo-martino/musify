from abc import ABCMeta

from syncify.local.file import File
from syncify.shared.core.base import Item


class LocalItem(File, Item, metaclass=ABCMeta):
    """Generic base class for locally-stored items"""

    __attributes_classes__ = (File, Item)

    def __hash__(self):  # TODO: why doesn't this get inherited correctly from File
        return super().__hash__()
