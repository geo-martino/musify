from typing import Self

from syncify.abstract.enums import Field, Fields, TagField, TagFields


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


class LocalTrackField(TrackFieldMixin):
    """Represent all currently supported fields for objects of type :py:class:`LocalTrack`"""
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

    # file properties
    PATH = TagFields.PATH.value
    FOLDER = TagFields.FOLDER.value
    FILENAME = TagFields.FILENAME.value
    EXT = TagFields.EXT.value
    SIZE = TagFields.SIZE.value
    KIND = TagFields.KIND.value
    CHANNELS = TagFields.CHANNELS.value
    BIT_RATE = TagFields.BIT_RATE.value
    BIT_DEPTH = TagFields.BIT_DEPTH.value
    SAMPLE_RATE = TagFields.SAMPLE_RATE.value

    # date properties
    DATE_MODIFIED = TagFields.DATE_MODIFIED.value
    DATE_ADDED = TagFields.DATE_ADDED.value
    LAST_PLAYED = TagFields.LAST_PLAYED.value

    # miscellaneous properties
    PLAY_COUNT = TagFields.PLAY_COUNT.value

    # remote properties
    URI = TagFields.URI.value


class PlaylistField(Field):
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
    ALL = Fields.ALL.value

    # tags/core properties
    ARTIST = Fields.ARTIST.value
    ALBUM = Fields.ALBUM.value
    ALBUM_ARTIST = Fields.ALBUM_ARTIST.value
    TRACK_TOTAL = Fields.TRACK_TOTAL.value
    GENRES = Fields.GENRES.value
    YEAR = Fields.YEAR.value
    DISC_TOTAL = Fields.DISC_TOTAL.value
    COMPILATION = Fields.COMPILATION.value
    IMAGES = Fields.IMAGES.value
    LENGTH = Fields.LENGTH.value
    RATING = Fields.RATING.value


class ArtistField(Field):
    ALL = Fields.ALL.value

    # tags/core properties
    ARTIST = Fields.ARTIST.value
    TRACK_TOTAL = Fields.TRACK_TOTAL.value
    GENRES = Fields.GENRES.value
    IMAGES = Fields.IMAGES.value
    LENGTH = Fields.LENGTH.value
    RATING = Fields.RATING.value
