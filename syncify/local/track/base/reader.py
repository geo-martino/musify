import re
from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Self

from PIL import Image

from syncify.local.track.base.processor import TagProcessor
from syncify.remote.enums import RemoteIDType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitIterable
from syncify.utils.helpers import to_collection


class TagReader(TagProcessor, metaclass=ABCMeta):
    """
    Contains methods for extracting tags from a loaded file
    
    :ivar uri_tag: The tag field to use as the URI tag in the file's metadata.
    :ivar num_sep: Some number values come as a combined string i.e. track number/track total
        Define the separator to use when representing both values as a combined string.
    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    """

    @property
    def name(self):
        return self.title if self.title else str(hash(self))

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
        """List of all artists featured on this track."""
        return self._artist.split(self.tag_sep)

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
    def year(self):
        return self._year

    @year.setter
    def year(self, value: int | None):
        self._year = value

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
        if value is None:
            self._uri = None
            self._has_uri = None
        elif self.remote_wrangler is not None and value == self.remote_wrangler.unavailable_uri_dummy:
            self._uri = None
            self._has_uri = False
        else:
            self._uri = value
            self._has_uri = True
        setattr(self, self.uri_tag.name.casefold(), value)

    @property
    def has_uri(self):
        return self._has_uri

    @property
    def image_links(self):
        return self._image_links

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
            return self.file.info.bits_per_sample / 1000
        except AttributeError:
            return None

    @property
    def sample_rate(self) -> float:
        """The sample rate of this track in kHz"""
        return self.file.info.sample_rate / 1000

    @property
    def date_added(self):
        return self._date_added

    @date_added.setter
    def date_added(self, value: datetime | None):
        self._date_added = value

    @property
    def last_played(self):
        return self._last_played

    @last_played.setter
    def last_played(self, value: datetime | None):
        self._last_played = value

    @property
    def play_count(self):
        return self._play_count

    @play_count.setter
    def play_count(self, value: datetime | None):
        self._play_count = value

    def __init__(self, remote_wrangler: RemoteDataWrangler = None):
        super().__init__()
        self.remote_wrangler = remote_wrangler

        self._title = None
        self._artist = None
        self._album = None
        self._album_artist = None
        self._track_number = None
        self._track_total = None
        self._genres = None
        self._year = None
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

    def load_metadata(self) -> Self:
        """General method for extracting metadata from loaded file"""
        self._read_metadata()
        return self

    def _read_metadata(self) -> None:
        """Driver for extracting metadata from a loaded file"""

        self.title = self._read_title()
        self.artist = self._read_artist()
        self.album = self._read_album()
        self.album_artist = self._read_album_artist()
        self.track_number = self._read_track_number()
        self.track_total = self._read_track_total()
        self.genres = self._read_genres()
        self.year = self._read_year()
        self.bpm = self._read_bpm()
        self.key = self._read_key()
        self.disc_number = self._read_disc_number()
        self.disc_total = self._read_disc_total()
        self.compilation = self._read_compilation()
        self.comments = self._read_comments()

        self.uri = self._read_uri()
        self.has_image = self._check_for_images()

    def _read_tag(self, tag_ids: Iterable[str]) -> list[Any] | None:
        """Extract all tag values from file for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            values.extend(value) if isinstance(value, (list, set, tuple)) else values.append(value)

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

    def _read_year(self) -> int | None:
        """Extract year tags from file"""
        values = self._read_tag(self.tag_map.year)
        if values is None:
            return

        try:
            year = int(re.sub(r"\D+", "", str(values[0]))[:4])
            return year if year > 1000 else None
        except (ValueError, TypeError):
            return

    def _read_bpm(self) -> float | None:
        """Extract bpm tags from file"""
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
        possible_values: tuple[str] | None = to_collection(self[self.uri_tag.name.casefold()])
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

    def _check_for_images(self) -> bool:
        """Check if file has embedded images"""
        return self._read_tag(self.tag_map.images) is not None
