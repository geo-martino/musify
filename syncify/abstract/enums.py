from enum import IntEnum
from typing import Self

from syncify.exception import SyncifyEnumError
from syncify.local.file import TagMap
from syncify.utils import UnitIterable


class SyncifyEnum(IntEnum):
    """Generic class for storing IntEnums."""

    @classmethod
    def all(cls) -> list[Self]:
        """Get all enums for this enum."""
        return [e for e in cls if e.name != "ALL"]

    @classmethod
    def from_name(cls, *names: str, fail_on_many: bool = True) -> list[Self]:
        """
        Returns the enums that match the given names

        :param fail_on_many: If more than one enum is found, raise an exception.
        :raise :py:class:`EnumNotFoundError`: If a corresponding enum cannot be found.
        """
        names_upper = [name.strip().upper() for name in names]
        enums = [enum for enum in cls if enum.name in names_upper]

        if len(enums) == 0:
            raise SyncifyEnumError(names)
        elif len(enums) > 1 and fail_on_many:
            raise SyncifyEnumError(value=enums, message="Too many enums found")

        return enums

    @classmethod
    def from_value(cls, *values: int, fail_on_many: bool = True) -> list[Self]:
        """
        Returns all enums that match the given enum name

        :param fail_on_many: If more than one enum is found, raise an exception.
        :raise :py:class:`EnumNotFoundError`: If a corresponding enum cannot be found.
        """
        enums = [enum for enum in cls if enum.value in values]
        if len(enums) == 0:
            raise SyncifyEnumError(values)
        elif len(enums) > 1 and fail_on_many:
            raise SyncifyEnumError(value=enums, message="Too many enums found")
        return enums


class Field(SyncifyEnum):
    """Base class for field names of an item."""

    @classmethod
    def map(cls, enum: Self) -> list[Self]:
        """Optional mapper to apply to the enum found during :py:meth:`from_name` and :py:meth:`from_value` calls"""
        return [enum]

    @classmethod
    def from_name(cls, *names: str) -> list[Self]:
        names_upper = [name.strip().upper() for name in names]
        enums = [e for enum in cls if enum.name in names_upper for e in cls.map(enum)]
        if len(enums) == 0:
            raise SyncifyEnumError(names)
        return enums

    @classmethod
    def from_value(cls, *values: int) -> list[Self]:
        enums = [e for enum in cls if enum.value in values for e in cls.map(enum)]
        if len(enums) == 0:
            raise SyncifyEnumError(values)
        return enums


class FieldCombined(Field):
    """
    Contains all possible Field enums in this program.

    This is used to ensure all Field enum implementations have the same values for their enum names.
    """
    # all numbers relate to the number of the field value as mapped by MusicBee
    # changing these numbers will break all MusicBee functionality unless it is noted
    # that a mapping with a MusicBee field is not present for that enum

    ALL = 0

    # tags/core properties
    TITLE = 65
    ARTIST = 32
    ALBUM = 30  # MusicBee album ignoring articles like 'the' and 'a' etc.
    ALBUM_ARTIST = 31
    TRACK_NUMBER = 86
    TRACK_TOTAL = 87
    GENRES = 59
    YEAR = 35
    BPM = 85
    KEY = 901  # unknown MusicBee mapping
    DISC_NUMBER = 52
    DISC_TOTAL = 54
    COMPILATION = 902  # unknown MusicBee mapping
    COMMENTS = 44
    IMAGES = 904  # no MusicBee mapping
    LENGTH = 16
    RATING = 75
    COMPOSER = 43
    CONDUCTOR = 45
    PUBLISHER = 73

    # file properties
    PATH = 106
    FOLDER = 179
    FILENAME = 52
    EXT = 100
    SIZE = 7
    KIND = 4
    CHANNELS = 8
    BIT_RATE = 10
    BIT_DEPTH = 183
    SAMPLE_RATE = 9

    # date properties
    DATE_CREATED = 921  # no MusicBee mapping
    DATE_MODIFIED = 11
    DATE_ADDED = 12
    LAST_PLAYED = 13

    # miscellaneous properties
    PLAY_COUNT = 14
    DESCRIPTION = 931  # no MusicBee mapping

    # remote properties
    URI = 941  # no MusicBee mapping
    USER_ID = 942  # no MusicBee mapping
    USER_NAME = 943  # no MusicBee mapping
    OWNER_ID = 944  # no MusicBee mapping
    OWNER_NAME = 945  # no MusicBee mapping
    FOLLOWERS = 946  # no MusicBee mapping


ALL_FIELDS = frozenset(FieldCombined.all())


class TagField(Field):
    """Applies extra functionality to the Field enum for Field types relating to :py:class:`Track` types"""

    __tags__ = frozenset(TagMap.__annotations__.keys())

    def to_tag(self) -> set[str]:
        """
        Returns all human-friendly tag names for the current enum value.

        Applies mapper to enums before returning as per :py:meth:`map`.
        This will only return tag names if they are found in :py:class:`TagMap`.
        """
        if self == FieldCombined.ALL:
            return {tag.name.lower() for tag in self.all() if tag.name.lower() in self.__tags__}
        return {tag.name.lower() for tag in self.map(self) if tag.name.lower() in self.__tags__}

    @classmethod
    def to_tags(cls, tags: UnitIterable[Self]) -> set[str]:
        """
        Returns all human-friendly tag names for the given enum value.

        Applies mapper to enums before returning as per :py:meth:`map`.
        This will only return tag names if they are found in :py:class:`TagMap`.
        """
        if isinstance(tags, cls):
            return tags.to_tag()
        return {t for tag in tags for t in tag.to_tag()}
