from typing import Self

from syncify.abstract.enums import Field, FieldCombined, TagField


class TrackFieldMixin(TagField):
    """Applies extra functionality to the Field enum for Field types relating to :py:class:`Track` types"""

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
    ALL = FieldCombined.ALL.value

    TITLE = FieldCombined.TITLE.value
    ARTIST = FieldCombined.ARTIST.value
    ALBUM = FieldCombined.ALBUM.value
    ALBUM_ARTIST = FieldCombined.ALBUM_ARTIST.value
    TRACK = FieldCombined.TRACK_NUMBER.value + 500
    TRACK_NUMBER = FieldCombined.TRACK_NUMBER.value
    TRACK_TOTAL = FieldCombined.TRACK_TOTAL.value
    GENRES = FieldCombined.GENRES.value
    YEAR = FieldCombined.YEAR.value
    BPM = FieldCombined.BPM.value
    KEY = FieldCombined.KEY.value
    DISC = FieldCombined.DISC_NUMBER.value + 500
    DISC_NUMBER = FieldCombined.DISC_NUMBER.value
    DISC_TOTAL = FieldCombined.DISC_TOTAL.value
    COMPILATION = FieldCombined.COMPILATION.value
    COMMENTS = FieldCombined.COMMENTS.value
    IMAGES = FieldCombined.IMAGES.value
    LENGTH = FieldCombined.LENGTH.value
    RATING = FieldCombined.RATING.value

    # remote properties
    URI = FieldCombined.URI.value


class LocalTrackField(TrackFieldMixin):
    """Represent all currently supported fields for objects of type :py:class:`LocalTrack`"""
    ALL = FieldCombined.ALL.value

    TITLE = FieldCombined.TITLE.value
    ARTIST = FieldCombined.ARTIST.value
    ALBUM = FieldCombined.ALBUM.value
    ALBUM_ARTIST = FieldCombined.ALBUM_ARTIST.value
    TRACK = FieldCombined.TRACK_NUMBER.value + 500
    TRACK_NUMBER = FieldCombined.TRACK_NUMBER.value
    TRACK_TOTAL = FieldCombined.TRACK_TOTAL.value
    GENRES = FieldCombined.GENRES.value
    YEAR = FieldCombined.YEAR.value
    BPM = FieldCombined.BPM.value
    KEY = FieldCombined.KEY.value
    DISC = FieldCombined.DISC_NUMBER.value + 500
    DISC_NUMBER = FieldCombined.DISC_NUMBER.value
    DISC_TOTAL = FieldCombined.DISC_TOTAL.value
    COMPILATION = FieldCombined.COMPILATION.value
    COMMENTS = FieldCombined.COMMENTS.value
    IMAGES = FieldCombined.IMAGES.value
    LENGTH = FieldCombined.LENGTH.value
    RATING = FieldCombined.RATING.value

    # file properties
    PATH = FieldCombined.PATH.value
    FOLDER = FieldCombined.FOLDER.value
    FILENAME = FieldCombined.FILENAME.value
    EXT = FieldCombined.EXT.value
    SIZE = FieldCombined.SIZE.value
    KIND = FieldCombined.KIND.value
    CHANNELS = FieldCombined.CHANNELS.value
    BIT_RATE = FieldCombined.BIT_RATE.value
    BIT_DEPTH = FieldCombined.BIT_DEPTH.value
    SAMPLE_RATE = FieldCombined.SAMPLE_RATE.value

    # date properties
    DATE_MODIFIED = FieldCombined.DATE_MODIFIED.value
    DATE_ADDED = FieldCombined.DATE_ADDED.value
    LAST_PLAYED = FieldCombined.LAST_PLAYED.value

    # miscellaneous properties
    PLAY_COUNT = FieldCombined.PLAY_COUNT.value

    # remote properties
    URI = FieldCombined.URI.value


class ArtistItemField(TagField):
    ALL = FieldCombined.ALL.value

    # tags/core properties
    ARTIST = FieldCombined.ARTIST.value
    GENRES = FieldCombined.GENRES.value
    IMAGES = FieldCombined.IMAGES.value
    RATING = FieldCombined.RATING.value

    # remote properties
    URI = FieldCombined.URI.value


class PlaylistField(Field):
    ALL = FieldCombined.ALL.value

    # tags/core properties
    TRACK_TOTAL = FieldCombined.TRACK_TOTAL.value
    IMAGES = FieldCombined.IMAGES.value
    LENGTH = FieldCombined.LENGTH.value

    # date properties
    DATE_CREATED = FieldCombined.DATE_CREATED.value
    DATE_MODIFIED = FieldCombined.DATE_MODIFIED.value

    # miscellaneous properties
    DESCRIPTION = FieldCombined.DESCRIPTION.value


class FolderField(Field):
    ALL = FieldCombined.ALL.value

    # tags/core properties
    TRACK_TOTAL = FieldCombined.TRACK_TOTAL.value
    GENRES = FieldCombined.GENRES.value
    IMAGES = FieldCombined.IMAGES.value
    COMPILATION = FieldCombined.COMPILATION.value
    LENGTH = FieldCombined.LENGTH.value

    # file properties
    FOLDER = FieldCombined.FOLDER.value


class AlbumField(Field):
    ALL = FieldCombined.ALL.value

    # tags/core properties
    ARTIST = FieldCombined.ARTIST.value
    ALBUM = FieldCombined.ALBUM.value
    ALBUM_ARTIST = FieldCombined.ALBUM_ARTIST.value
    TRACK_TOTAL = FieldCombined.TRACK_TOTAL.value
    GENRES = FieldCombined.GENRES.value
    YEAR = FieldCombined.YEAR.value
    DISC_TOTAL = FieldCombined.DISC_TOTAL.value
    COMPILATION = FieldCombined.COMPILATION.value
    IMAGES = FieldCombined.IMAGES.value
    LENGTH = FieldCombined.LENGTH.value
    RATING = FieldCombined.RATING.value


class ArtistField(Field):
    ALL = FieldCombined.ALL.value

    # tags/core properties
    ARTIST = FieldCombined.ARTIST.value
    TRACK_TOTAL = FieldCombined.TRACK_TOTAL.value
    GENRES = FieldCombined.GENRES.value
    IMAGES = FieldCombined.IMAGES.value
    LENGTH = FieldCombined.LENGTH.value
    RATING = FieldCombined.RATING.value
