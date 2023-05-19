from abc import ABCMeta, abstractmethod
from typing import Optional

import mutagen

from syncify.abstract.item import Track
from syncify.enums.tags import TagName, TagMap


class TagProcessor(Track, metaclass=ABCMeta):
    """Generic base class for tag processing"""

    uri_tag = TagName.COMMENTS

    @property
    @abstractmethod
    def _num_sep(self) -> str:
        """
        Some number values come as a combined string i.e. track number/track total
        Define the separator to use when representing both values as a combined string
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def tag_map(self) -> TagMap:
        raise NotImplementedError

    @property
    @abstractmethod
    def path(self) -> Optional[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def file(self) -> Optional[mutagen.File]:
        raise NotImplementedError

    @abstractmethod
    def load_file(self) -> Optional[mutagen.File]:
        """
        Load local file using mutagen and set object file path and extension properties.

        :returns: Mutagen file object or None if load error.
        :exception FileNotFoundError: If the file cannot be found.
        :exception IllegalFileTypeError: If the file type is not supported.
        """
