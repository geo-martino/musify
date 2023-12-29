from typing import Self

from syncify.abstract.enums import Field, FieldCombined, TagField, TagFieldCombined


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
    ALL = TagFieldCombined.ALL.value

    TITLE = TagFieldCombined.TITLE.value
    ARTIST = TagFieldCombined.ARTIST.value
    ALBUM = TagFieldCombined.ALBUM.value
    ALBUM_ARTIST = TagFieldCombined.ALBUM_ARTIST.value
    TRACK = TagFieldCombined.TRACK_NUMBER.value + 500
    TRACK_NUMBER = TagFieldCombined.TRACK_NUMBER.value
    TRACK_TOTAL = TagFieldCombined.TRACK_TOTAL.value
    GENRES = TagFieldCombined.GENRES.value
    YEAR = TagFieldCombined.YEAR.value
    BPM = TagFieldCombined.BPM.value
    KEY = TagFieldCombined.KEY.value
    DISC = TagFieldCombined.DISC_NUMBER.value + 500
    DISC_NUMBER = TagFieldCombined.DISC_NUMBER.value
    DISC_TOTAL = TagFieldCombined.DISC_TOTAL.value
    COMPILATION = TagFieldCombined.COMPILATION.value
    COMMENTS = TagFieldCombined.COMMENTS.value
    IMAGES = TagFieldCombined.IMAGES.value
    LENGTH = TagFieldCombined.LENGTH.value
    RATING = TagFieldCombined.RATING.value

    # remote properties
    URI = TagFieldCombined.URI.value


class LocalTrackField(TrackFieldMixin):
    """Represent all currently supported fields for objects of type :py:class:`LocalTrack`"""
    ALL = TagFieldCombined.ALL.value

    TITLE = TagFieldCombined.TITLE.value
    ARTIST = TagFieldCombined.ARTIST.value
    ALBUM = TagFieldCombined.ALBUM.value
    ALBUM_ARTIST = TagFieldCombined.ALBUM_ARTIST.value
    TRACK = TagFieldCombined.TRACK_NUMBER.value + 500
    TRACK_NUMBER = TagFieldCombined.TRACK_NUMBER.value
    TRACK_TOTAL = TagFieldCombined.TRACK_TOTAL.value
    GENRES = TagFieldCombined.GENRES.value
    YEAR = TagFieldCombined.YEAR.value
    BPM = TagFieldCombined.BPM.value
    KEY = TagFieldCombined.KEY.value
    DISC = TagFieldCombined.DISC_NUMBER.value + 500
    DISC_NUMBER = TagFieldCombined.DISC_NUMBER.value
    DISC_TOTAL = TagFieldCombined.DISC_TOTAL.value
    COMPILATION = TagFieldCombined.COMPILATION.value
    COMMENTS = TagFieldCombined.COMMENTS.value
    IMAGES = TagFieldCombined.IMAGES.value
    LENGTH = TagFieldCombined.LENGTH.value
    RATING = TagFieldCombined.RATING.value

    # file properties
    PATH = TagFieldCombined.PATH.value
    FOLDER = TagFieldCombined.FOLDER.value
    FILENAME = TagFieldCombined.FILENAME.value
    EXT = TagFieldCombined.EXT.value
    SIZE = TagFieldCombined.SIZE.value
    KIND = TagFieldCombined.KIND.value
    CHANNELS = TagFieldCombined.CHANNELS.value
    BIT_RATE = TagFieldCombined.BIT_RATE.value
    BIT_DEPTH = TagFieldCombined.BIT_DEPTH.value
    SAMPLE_RATE = TagFieldCombined.SAMPLE_RATE.value

    # date properties
    DATE_MODIFIED = TagFieldCombined.DATE_MODIFIED.value
    DATE_ADDED = TagFieldCombined.DATE_ADDED.value
    LAST_PLAYED = TagFieldCombined.LAST_PLAYED.value

    # miscellaneous properties
    PLAY_COUNT = TagFieldCombined.PLAY_COUNT.value

    # remote properties
    URI = TagFieldCombined.URI.value


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
