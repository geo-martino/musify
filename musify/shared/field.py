"""
All core :py:class:`Field` implementations relating to
core :py:class:`Item` and :py:class`ItemCollection` implementations.
"""

from typing import Self

from musify.shared.core.enum import Field, Fields, TagField, TagFields


class TrackFieldMixin(TagField):
    """Applies extra functionality to the TagField enum for TagField types relating to :py:class:`Track` types"""

    # noinspection PyUnresolvedReferences
    @classmethod
    def map(cls, enum: Self) -> list[Self]:
        """
        Mapper to apply to the enum found during :py:meth:`from_name` and :py:meth:`from_value` calls,
        or from :py:meth:`to_tag` and :py:meth:`to_tags` calls

        Applies the following mapping:
            * ``TRACK`` returns both ``TRACK_NUMBER`` and ``TRACK_TOTAL`` enums
            * ``DISC`` returns both ``DISC_NUMBER`` and ``DISC_TOTAL`` enums
            * all other enums return the enum in a unit list
        """
        if enum == cls.TRACK:
            return [cls.TRACK_NUMBER, cls.TRACK_TOTAL]
        elif enum == cls.DISC:
            return [cls.DISC_NUMBER, cls.DISC_TOTAL]
        return [enum]


class TrackField(TrackFieldMixin):
    """Represent all currently supported fields for objects of type :py:class:`Track`"""
    ALL = TagFields.ALL.value

    TITLE = TagFields.TITLE.value
    ARTIST = TagFields.ARTIST.value
    ALBUM = TagFields.ALBUM.value
    ALBUM_ARTIST = TagFields.ALBUM_ARTIST.value
    TRACK = TagFields.TRACK_NUMBER.value + 500
    TRACK_NUMBER = TagFields.TRACK_NUMBER.value
    TRACK_TOTAL = TagFields.TRACK_TOTAL.value
    GENRES = TagFields.GENRES.value
    YEAR = TagFields.YEAR.value
    BPM = TagFields.BPM.value
    KEY = TagFields.KEY.value
    DISC = TagFields.DISC_NUMBER.value + 500
    DISC_NUMBER = TagFields.DISC_NUMBER.value
    DISC_TOTAL = TagFields.DISC_TOTAL.value
    COMPILATION = TagFields.COMPILATION.value
    COMMENTS = TagFields.COMMENTS.value
    IMAGES = TagFields.IMAGES.value
    LENGTH = TagFields.LENGTH.value
    RATING = TagFields.RATING.value

    # remote properties
    URI = TagFields.URI.value


class PlaylistField(Field):
    """Represent all currently supported fields for objects of type :py:class:`Playlist`"""
    ALL = Fields.ALL.value

    # tags/core properties
    TRACK_TOTAL = Fields.TRACK_TOTAL.value
    IMAGES = Fields.IMAGES.value
    LENGTH = Fields.LENGTH.value

    # date properties
    DATE_CREATED = Fields.DATE_CREATED.value
    DATE_MODIFIED = Fields.DATE_MODIFIED.value

    # miscellaneous properties
    DESCRIPTION = Fields.DESCRIPTION.value


class FolderField(Field):
    """Represent all currently supported fields for objects of type :py:class:`Folder`"""
    ALL = Fields.ALL.value

    # tags/core properties
    TRACK_TOTAL = Fields.TRACK_TOTAL.value
    GENRES = Fields.GENRES.value
    IMAGES = Fields.IMAGES.value
    COMPILATION = Fields.COMPILATION.value
    LENGTH = Fields.LENGTH.value

    # file properties
    FOLDER = Fields.FOLDER.value


class AlbumField(Field):
    """Represent all currently supported fields for objects of type :py:class:`Album`"""
    ALL = Fields.ALL.value

    # tags/core properties
    ARTIST = Fields.ARTIST.value
    ALBUM = Fields.ALBUM.value
    ALBUM_ARTIST = Fields.ALBUM_ARTIST.value
    TRACK_TOTAL = Fields.TRACK_TOTAL.value
    GENRES = Fields.GENRES.value
    DATE = TagFields.DATE.value
    YEAR = TagFields.YEAR.value
    MONTH = TagFields.MONTH.value
    DAY = TagFields.DAY.value
    DISC_TOTAL = Fields.DISC_TOTAL.value
    COMPILATION = Fields.COMPILATION.value
    IMAGES = Fields.IMAGES.value
    LENGTH = Fields.LENGTH.value
    RATING = Fields.RATING.value


class ArtistField(Field):
    """Represent all currently supported fields for objects of type :py:class:`Artist`"""
    ALL = Fields.ALL.value

    # tags/core properties
    ARTIST = Fields.ARTIST.value
    TRACK_TOTAL = Fields.TRACK_TOTAL.value
    GENRES = Fields.GENRES.value
    IMAGES = Fields.IMAGES.value
    LENGTH = Fields.LENGTH.value
    RATING = Fields.RATING.value
