from abc import ABCMeta, abstractmethod, ABC
from dataclasses import dataclass
from typing import List

from syncify.abstract import PrettyPrinter


class Item(PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing an item."""


class ItemCollection(PrettyPrinter, metaclass=ABCMeta):
    """Generic class for storing a collection of items."""

    @property
    @abstractmethod
    def items(self) -> List[Item]:
        raise NotImplementedError

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (t for t in self.items)


@dataclass
class SyncResult(ABC):
    pass
