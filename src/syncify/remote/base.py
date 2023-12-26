from abc import ABC, abstractmethod


class Remote(ABC):
    """Generic base class for remote objects"""

    @property
    @abstractmethod
    def remote_source(self) -> str:
        """Name for the remote source"""
        raise NotImplementedError
