"""
Implements all functionality pertaining to reading metadata/tags/properties of a :py:class:`LocalTrack`.
"""

import datetime
import re
from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any

import mutagen
from PIL import Image

from musify.local.base import LocalItem
from musify.local.track.field import LocalTrackField
from musify.shared.core.enum import TagMap
from musify.shared.core.object import Track
from musify.shared.exception import MusifyValueError
from musify.shared.remote.enum import RemoteIDType
from musify.shared.remote.processors.wrangle import RemoteDataWrangler
from musify.shared.types import UnitIterable
from musify.shared.utils import to_collection


class TagReader(LocalItem, Track, metaclass=ABCMeta):
    """
    Functionality for reading tags/metadata/properties from a loaded audio file.

    :param remote_wrangler: Optionally, provide a :py:class:`RemoteDataWrangler` object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    """

    __slots__ = (
        "remote_wrangler",
        "_title",
        "_artist",
        "_album",
        "_album_artist",
        "_track_number",
        "_track_total",
        "_genres",
        "_year",
        "_month",
        "_day",
        "_bpm",
        "_key",
        "_disc_number",
        "_disc_total",
        "_compilation",
        "_comments",
        "_uri",
        "_has_uri",
        "_image_links",
        "_has_image",
        "_rating",
        "_date_added",
        "_last_played",
        "_play_count",
        "_loaded",
    )
    __attributes_classes__ = (LocalItem, Track)
    __attributes_ignore__ = ("tag_map", "file")

    #: The tag field to use as the URI tag in the file's metadata
    uri_tag: LocalTrackField = LocalTrackField.COMMENTS
    #: The separator to use when representing separated tag values as a combined string.
    #: Used when some number type tag values come as a combined string i.e. track number/track total
    num_sep: str = "/"

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

    @property
    def name(self):
        return self.title or self.filename

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value: str | None):
        self._title = value

    @property
    def artist(self):
        return self._artist

    @artist.setter
    def artist(self, value: str | None):
        self._artist = value

    @property
    def artists(self) -> list[str]:
        return self._artist.split(self.tag_sep) if self._artist else []

    @artists.setter
    def artists(self, value: list[str]):
        self._artist = self.tag_sep.join(value)

    @property
    def album(self):
        return self._album

    @album.setter
    def album(self, value: str | None):
        self._album = value

    @property
    def album_artist(self):
        return self._album_artist

    @album_artist.setter
    def album_artist(self, value: str | None):
        self._album_artist = value

    @property
    def track_number(self):
        return self._track_number

    @track_number.setter
    def track_number(self, value: int | None):
        self._track_number = value

    @property
    def track_total(self):
        return self._track_total

    @track_total.setter
    def track_total(self, value: int | None):
        self._track_total = value

    @property
    def genres(self):
        return self._genres

    @genres.setter
    def genres(self, value: list[str] | None):
        self._genres = value

    @property
    def date(self):
        if self._year and self._month and self._day:
            return datetime.date(self._year, self._month, self._day)

    @date.setter
    def date(self, value: datetime.date | None):
        self._year = value.year if value else None
        self._month = value.month if value else None
        self._day = value.day if value else None

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, value: int | None):
        if value and value < 1000:
            raise MusifyValueError(f"Year value is invalid: {value}")
        self._year = value

    @property
    def month(self):
        return self._month

    @month.setter
    def month(self, value: int | None):
        if value and (value < 1 or value > 12):
            raise MusifyValueError(f"Month value is invalid: {value}")
        self._month = value

    @property
    def day(self):
        return self._day

    @day.setter
    def day(self, value: int | None):
        if value and (value < 1 or value > 31):
            raise MusifyValueError(f"Day value is invalid: {value}")
        self._day = value

    @property
    def bpm(self):
        return self._bpm

    @bpm.setter
    def bpm(self, value: float | None):
        self._bpm = value

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value: str | None):
        self._key = value

    @property
    def disc_number(self):
        return self._disc_number

    @disc_number.setter
    def disc_number(self, value: int | None):
        self._disc_number = value

    @property
    def disc_total(self):
        return self._disc_total

    @disc_total.setter
    def disc_total(self, value: int | None):
        self._disc_total = value

    @property
    def compilation(self):
        return self._compilation

    @compilation.setter
    def compilation(self, value: bool | None):
        self._compilation = value

    @property
    def comments(self):
        return self._comments

    @comments.setter
    def comments(self, value: UnitIterable[str] | None):
        self._comments = [value] if isinstance(value, str) else to_collection(value, list)

    @property
    def uri(self):
        return self._uri

    @uri.setter
    def uri(self, value: str | None):
        """Set both the ``uri`` property and the ``has_uri`` property ."""
        if value is None:
            self._uri = None
            self._has_uri = None
        elif self.remote_wrangler is not None and value == self.remote_wrangler.unavailable_uri_dummy:
            self._uri = None
            self._has_uri = False
        else:
            self._uri = value
            self._has_uri = True

        if self._loaded:
            setattr(self, self.uri_tag.name.lower(), value)

    @property
    def has_uri(self):
        return self._has_uri

    @property
    def image_links(self):
        return self._image_links

    @image_links.setter
    def image_links(self, value: dict[str, str]):
        self._image_links = value

    @property
    def has_image(self):
        return self._has_image

    @has_image.setter
    def has_image(self, value: bool):
        self._has_image = value

    @property
    def length(self):
        return self.file.info.length

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, value: float | None):
        self._rating = value

    @property
    def path(self):
        return self.file.filename

    @property
    def kind(self):
        """The kind of audio file of this track"""
        return self.__class__.__name__

    @property
    def channels(self) -> int:
        """The number of channels in this audio file i.e. 1 for mono, 2 for stereo, ..."""
        return self.file.info.channels

    @property
    def bit_rate(self) -> float:
        """The bit rate of this track in kilobytes per second"""
        return self.file.info.bitrate / 1000

    @property
    def bit_depth(self) -> int | None:
        """The bit depth of this track in bits"""
        try:
            return self.file.info.bits_per_sample
        except AttributeError:
            return None

    @property
    def sample_rate(self) -> float:
        """The sample rate of this track in kHz"""
        return self.file.info.sample_rate / 1000

    @property
    def date_added(self) -> datetime.datetime | None:
        """The timestamp for when this track was added to the associated collection"""
        return self._date_added

    @date_added.setter
    def date_added(self, value: datetime.datetime | None):
        self._date_added = value

    @property
    def last_played(self) -> datetime.datetime | None:
        """The timestamp when this track was last played"""
        return self._last_played

    @last_played.setter
    def last_played(self, value: datetime.datetime | None):
        self._last_played = value

    @property
    def play_count(self) -> int | None:
        """The total number of times this track has been played"""
        return self._play_count

    @play_count.setter
    def play_count(self, value: int | None):
        self._play_count = value

    def __init__(self, remote_wrangler: RemoteDataWrangler = None):
        super().__init__()
        #: A :py:class:`RemoteDataWrangler` object for processing URIs
        self.remote_wrangler = remote_wrangler

        self._title = None
        self._artist = None
        self._album = None
        self._album_artist = None
        self._track_number = None
        self._track_total = None
        self._genres = None
        self._year = None
        self._month = None
        self._day = None
        self._bpm = None
        self._key = None
        self._disc_number = None
        self._disc_total = None
        self._compilation = None
        self._comments = None

        self._uri = None
        self._has_uri = None
        self._has_image = None
        self._image_links = {}

        self._rating = None
        self._date_added = None
        self._last_played = None
        self._play_count = None

        self._loaded = False

    def load_metadata(self) -> None:
        """Driver for extracting all supported metadata from a loaded file"""

        self.title = self._read_title()
        self.artist = self._read_artist()
        self.album = self._read_album()
        self.album_artist = self._read_album_artist()
        self.track_number = self._read_track_number()
        self.track_total = self._read_track_total()
        self.genres = self._read_genres()
        self.year, self.month, self.day = self._read_date() or (None, None, None)
        self.bpm = self._read_bpm()
        self.key = self._read_key()
        self.disc_number = self._read_disc_number()
        self.disc_total = self._read_disc_total()
        self.compilation = self._read_compilation()
        self.comments = self._read_comments()

        self.uri = self._read_uri()
        self.has_image = self._check_for_images()

        self._loaded = True

    def _read_tag(self, tag_ids: Iterable[str]) -> list[Any] | None:
        """Extract all tag values from file for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            if isinstance(value, (list, set, tuple)) and all(isinstance(val, str) for val in value):
                values.extend(v for val in value for v in val.split('\x00'))
            elif isinstance(value, (list, set, tuple)):
                values.extend(value)
            elif isinstance(value, str):
                values.extend(value.split('\x00'))
            else:
                values.append(value)

        return values if len(values) > 0 else None

    def _read_title(self) -> str | None:
        """Extract track title tags from file"""
        values = self._read_tag(self.tag_map.title)
        return str(values[0]) if values is not None else None

    def _read_artist(self) -> str | None:
        """Extract artist tags from file"""
        values = self._read_tag(self.tag_map.artist)
        return str(values[0]) if values is not None else None

    def _read_album(self) -> str | None:
        """Extract album tags from file"""
        values = self._read_tag(self.tag_map.album)
        return str(values[0]) if values is not None else None

    def _read_album_artist(self) -> str | None:
        """Extract album artist tags from file"""
        values = self._read_tag(self.tag_map.album_artist)
        return str(values[0]) if values is not None else None

    def _read_track_number(self) -> int | None:
        """Extract track number tags from file"""
        values = self._read_tag(self.tag_map.track_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self.num_sep)[0]) if self.num_sep in value else int(value)

    def _read_track_total(self) -> int | None:
        """Extract total track count tags from file"""
        values = self._read_tag(self.tag_map.track_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self.num_sep)[1]) if self.num_sep in value else int(value)

    def _read_genres(self) -> list[str] | None:
        """Extract genre tags from file"""
        values = self._read_tag(self.tag_map.genres)
        return list(map(str, values)) if values is not None else None

    def _read_date(self) -> tuple[int | None, int | None, int | None] | None:
        """Extract year tags from file"""
        values = self._read_tag(self.tag_map.date)

        if values is None:  # attempt to read each part individually
            year = self._read_tag(self.tag_map.year)
            year = int(re.match(r"(\d{4})", str(year[0])).group(1)) if year else None
            month = self._read_tag(self.tag_map.month)
            month = int(re.match(r"(\d{1,2})", str(month[0])).group(1)) if month else None
            day = self._read_tag(self.tag_map.day)
            day = int(re.match(r"(\d{1,2})", str(day[0])).group(1)) if day else None
            return year, month, day
        elif 0 < len(values) <= 3 and all(str(value).isdigit() for value in values):
            values = ["/".join(values)]  # just join to string and allow later regex matches to determine format

        # YYYY-MM-DD
        match = re.match(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", str(values[0]))
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))

        # DD-MM-YY
        match = re.match(r"(\d{1,2})\D+(\d{1,2})\D+(\d{4})", str(values[0]))
        if match:
            return int(match.group(3)), int(match.group(2)), int(match.group(1))

        # YYYY-MM
        match = re.match(r"(\d{4})\D+(\d{1,2})", str(values[0]))
        if match:
            return int(match.group(1)), int(match.group(2)), None

        # MM-YYYY
        match = re.match(r"(\d{4})\D+(\d{1,2})", str(values[0]))
        if match:
            return int(match.group(2)), int(match.group(1)), None

        # YYYY
        match = re.match(r"(\d{4})", str(values[0]))
        if match:
            return int(match.group(1)), None, None

    def _read_bpm(self) -> float | None:
        """Extract BPM tags from file"""
        values = self._read_tag(self.tag_map.bpm)
        return float(values[0]) if values is not None else None

    def _read_key(self) -> str | None:
        """Extract key tags from file"""
        values = self._read_tag(self.tag_map.key)
        return str(values[0]) if values is not None else None

    def _read_disc_number(self) -> int | None:
        """Extract disc number tags from file"""
        values = self._read_tag(self.tag_map.disc_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self.num_sep)[0]) if self.num_sep in value else int(value)

    def _read_disc_total(self) -> int | None:
        """Extract total disc count tags from file"""
        values = self._read_tag(self.tag_map.disc_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self.num_sep)[1]) if self.num_sep in value else int(value)

    def _read_compilation(self) -> bool | None:
        """Extract compilation tags from file"""
        values = self._read_tag(self.tag_map.compilation)
        return bool(int(values[0])) if values is not None else None

    def _read_comments(self) -> list[str] | None:
        """Extract comment tags from file"""
        values = self._read_tag(self.tag_map.comments)
        return list({str(value) for value in values}) if values is not None else None

    def _read_uri(self) -> str | None:
        """Extract data relating to remote URI value from file"""
        wrangler = self.remote_wrangler
        if not wrangler:
            return

        # WORKAROUND: for dodgy MP3 tag comments, split on null and take first value
        possible_values: tuple[str, ...] | None = to_collection(self[self.uri_tag.name.lower()])
        if not possible_values:
            return None

        # WORKAROUND: for dodgy MP3 tag comments, split on null and take first value
        possible_values = tuple(val for values in possible_values for val in values.split("\x00"))
        for uri in possible_values:
            if uri == wrangler.unavailable_uri_dummy or wrangler.validate_id_type(uri, kind=RemoteIDType.URI):
                return uri

        return None

    @abstractmethod
    def _read_images(self) -> list[Image.Image] | None:
        """Extract image from file"""
        raise NotImplementedError

    def _check_for_images(self) -> bool:
        """Check if file has embedded images"""
        return self._read_tag(self.tag_map.images) is not None
