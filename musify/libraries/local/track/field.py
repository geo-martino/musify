"""
The core Field enum for a :py:class:`LocalTrack` representing all possible tags/metadata/properties.
"""
from musify.field import TagFields, Fields
from musify.field import TrackFieldMixin


class LocalTrackField(TrackFieldMixin):
    """Represents all currently supported fields for objects of type :py:class:`LocalTrack`"""
    ALL = TagFields.ALL.value

    TITLE = TagFields.TITLE.value
    ARTIST = TagFields.ARTIST.value
    ARTISTS = Fields.ARTISTS.value
    ALBUM = TagFields.ALBUM.value
    ALBUM_ARTIST = TagFields.ALBUM_ARTIST.value
    TRACK = TagFields.TRACK_NUMBER.value + 500
    TRACK_NUMBER = TagFields.TRACK_NUMBER.value
    TRACK_TOTAL = TagFields.TRACK_TOTAL.value
    GENRES = TagFields.GENRES.value
    DATE = TagFields.DATE.value
    YEAR = TagFields.YEAR.value
    MONTH = TagFields.MONTH.value
    DAY = TagFields.DAY.value
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
    TYPE = TagFields.TYPE.value
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
