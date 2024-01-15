from abc import ABC, abstractmethod


class Remote(ABC):
    """Generic base class for remote objects"""

    @property
    @abstractmethod
    def source(self) -> str:
        """The type of remote library loaded (i.e. the data source)"""
        raise NotImplementedError
