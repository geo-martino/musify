from abc import ABCMeta, abstractmethod

import mutagen

from syncify.abstract.item import Track, TrackProperties
from syncify.enums.tags import TagName, TagMap
from syncify.local.base import LocalObject
from syncify.local.file import File


class TagProcessor(Track, TrackProperties, LocalObject, File, metaclass=ABCMeta):
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
        """Map of human-friendly tag name to ID3 tag ids for a given file type"""
        raise NotImplementedError

    @property
    @abstractmethod
    def file(self) -> mutagen.FileType:
        """The mutagen file object representing the loaded file."""
        raise NotImplementedError

    @abstractmethod
    def get_file(self) -> mutagen.FileType:
        """
        Load local file using mutagen and set object file path and extension properties.

        :returns: Mutagen file object or None if load error.
        :raises FileNotFoundError: If the file cannot be found.
        :raises IllegalFileTypeError: If the file type is not supported.
        """
