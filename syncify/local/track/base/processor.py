from abc import ABCMeta, abstractmethod
from datetime import datetime

import mutagen

from syncify.abstract.item import Track
from syncify.fields import LocalTrackField
from syncify.local.base import LocalItem
from syncify.local.file import TagMap


class TagProcessor(LocalItem, Track, metaclass=ABCMeta):
    """
    Generic base class for tag processing
    
    :ivar uri_tag: The tag field to use as the URI tag in the file's metadata.
    :ivar num_sep: Some number values come as a combined string i.e. track number/track total
        Define the separator to use when representing both values as a combined string.
    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    """

    uri_tag: LocalTrackField = LocalTrackField.COMMENTS
    num_sep: str = "/"

    @property
    @abstractmethod
    def date_added(self) -> datetime | None:
        """The timestamp for when this track was added to the associated collection"""
        raise NotImplementedError

    @property
    @abstractmethod
    def last_played(self) -> datetime | None:
        """The timestamp when this track was last played"""
        raise NotImplementedError

    @property
    @abstractmethod
    def play_count(self) -> int | None:
        """The total number of times this track has been played"""
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

    def __init__(self):
        LocalItem.__init__(self)
        Track.__init__(self)

    @abstractmethod
    def get_file(self) -> mutagen.FileType:
        """
        Load local file using mutagen and set object file path and extension properties.

        :return: Mutagen file object or None if load error.
        :raise FileNotFoundError: If the file cannot be found.
        :raise InvalidFileType: If the file type is not supported.
        """
