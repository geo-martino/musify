"""
Compositely combine reader and writer classes for metadata/tags/properties operations on Track files.
"""
import datetime
import os
from abc import ABCMeta, abstractmethod
from copy import deepcopy
from os.path import join, exists, dirname
from typing import Any, Self

import mutagen

from musify.core.base import MusifyItem
from musify.core.enum import TagMap
from musify.exception import MusifyKeyError, MusifyAttributeError, MusifyTypeError, MusifyValueError
from musify.field import TrackField
from musify.file.exception import FileDoesNotExistError
from musify.libraries.core.object import Track
from musify.libraries.local.base import LocalItem
from musify.libraries.local.track.field import LocalTrackField as Tags
from musify.libraries.local.track.tags.reader import TagReader
from musify.libraries.local.track.tags.writer import TagWriter, SyncResultTrack
from musify.libraries.remote.core.processors.wrangle import RemoteDataWrangler
from musify.types import UnitIterable
from musify.utils import to_collection


class LocalTrack[T: mutagen.FileType, U: TagReader, V: TagWriter](LocalItem, Track, metaclass=ABCMeta):
    """
    Generic track object for extracting, modifying, and saving metadata/tags/properties for a given file.

    :param file: The path or Mutagen object of the file to load.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    """

    __slots__ = (
        "_reader",
        "_writer",
        "_loaded",
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
    )
    __attributes_classes__ = (Track, LocalItem)
    __attributes_ignore__ = "tag_map"

    @property
    def name(self):
        return self.title or self.filename

    @property
    @abstractmethod
    def tag_map(self) -> TagMap:
        """The map of tag names to tag IDs for the given file type."""
        raise NotImplementedError

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

    def _uri_getter(self):
        return self._uri

    def _uri_setter(self, value: str | None):
        if value is None:
            self._uri = None
            self._has_uri = None
        elif self._reader.unavailable_uri_dummy is not None and value == self._reader.unavailable_uri_dummy:
            self._uri = None
            self._has_uri = False
        else:
            self._uri = value
            self._has_uri = True

        if self._loaded:
            setattr(self, self._reader.uri_tag.name.lower(), value)

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
        return self._reader.file.info.length

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, value: float | None):
        self._rating = value

    @property
    def path(self):
        return self._reader.file.filename

    @property
    def type(self):
        """The type of audio file of this track"""
        return self.__class__.__name__

    @property
    def channels(self) -> int:
        """The number of channels in this audio file i.e. 1 for mono, 2 for stereo, ..."""
        return self._reader.file.info.channels

    @property
    def bit_rate(self) -> float:
        """The bit rate of this track in kilobytes per second"""
        return self._reader.file.info.bitrate / 1000

    @property
    def bit_depth(self) -> int | None:
        """The bit depth of this track in bits"""
        try:
            return self._reader.file.info.bits_per_sample
        except AttributeError:
            return None

    @property
    def sample_rate(self) -> float:
        """The sample rate of this track in kHz"""
        return self._reader.file.info.sample_rate / 1000

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

    @staticmethod
    @abstractmethod
    def _create_reader(*args, **kwargs) -> U:
        """Return a :py:class:`TagReader` object for this track type"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def _create_writer(*args, **kwargs) -> V:
        """Return a :py:class:`TagWriter` object for this track type"""
        raise NotImplementedError

    def __init__(self, file: str | T, remote_wrangler: RemoteDataWrangler = None):
        super().__init__()

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

        file: T = self.load(file) if isinstance(file, str) else file
        self._reader = self._create_reader(file=file, tag_map=self.tag_map, remote_wrangler=remote_wrangler)
        self._writer = self._create_writer(file=file, tag_map=self.tag_map, remote_wrangler=remote_wrangler)
        self.refresh()

    def load(self, path: str | None = None) -> T:
        """
        Load local file using mutagen from the given path or the path stored in the object's ``file``.
        Re-formats to case-sensitive system path if applicable.

        :param path: The path to the file. If not given, use the stored ``file`` path.
        :return: Mutagen file object or None if load error.
        :raise FileDoesNotExistError: If the file cannot be found.
        :raise InvalidFileType: If the file type is not supported.
        """
        path = path or self.path
        self._validate_type(path)

        if not path or not exists(path):
            raise FileDoesNotExistError(f"File not found | {path}")

        return mutagen.File(path)

    def refresh(self) -> None:
        """Extract update tags for this object from the loaded mutagen object."""

        self.title = self._reader.read_title()
        self.artist = self._reader.read_artist()
        self.album = self._reader.read_album()
        self.album_artist = self._reader.read_album_artist()
        self.track_number = self._reader.read_track_number()
        self.track_total = self._reader.read_track_total()
        self.genres = self._reader.read_genres()
        self.year, self.month, self.day = self._reader.read_date() or (None, None, None)
        self.bpm = self._reader.read_bpm()
        self.key = self._reader.read_key()
        self.disc_number = self._reader.read_disc_number()
        self.disc_total = self._reader.read_disc_total()
        self.compilation = self._reader.read_compilation()
        self.comments = self._reader.read_comments()

        self.uri = self._reader.read_uri()
        self.has_image = self._reader.check_for_images()

        self._loaded = True

    def save(self, tags: UnitIterable[Tags] = Tags.ALL, replace: bool = False, dry_run: bool = True) -> SyncResultTrack:
        """
        Update file's tags from given dictionary of tags.

        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :param dry_run: Run function, but do not modify the file on the disk.
        :return: List of tags that have been updated.
        """
        # reload the mutagen object in place to ensure comparison are being made against current data
        self._writer.file.load(self._writer.file.filename)

        current = deepcopy(self)
        current.refresh()

        return self._writer.write(source=current, target=self, tags=tags, replace=replace, dry_run=dry_run)

    def delete_tags(self, tags: UnitIterable[Tags] = (), dry_run: bool = True) -> SyncResultTrack:
        """
        Remove tags from file.

        :param tags: Tags to remove.
        :param dry_run: Run function, but do not modify the file on the disk.
        :return: List of tags that have been removed.
        """
        result = self._writer.delete_tags(tags=tags, dry_run=dry_run)
        if Tags.IMAGES in result.updated:
            self.has_image = False
        return result

    def merge(self, track: Track, tags: UnitIterable[TrackField] = TrackField.ALL) -> None:
        """Set the tags of this track equal to the given ``track``. Give a list of ``tags`` to limit which are set"""
        tag_names = TrackField.__tags__ if tags == TrackField.ALL else set(TrackField.to_tags(tags))

        for tag in tag_names:  # merge on each tag
            if hasattr(track, tag):
                setattr(self, tag, deepcopy(track[tag]))

    def extract_images_to_file(self, output_folder: str) -> int:
        """Extract and save all embedded images from file. Returns the number of images extracted."""
        images = self._reader.read_images()
        if images is None:
            return False
        count = 0

        for i, image in enumerate(images):
            output_path = join(output_folder, self.filename + f"_{str(i).zfill(2)}" + image.format.lower())
            os.makedirs(dirname(output_path), exist_ok=True)

            image.save(output_path)
            count += 1

        return count

    def as_dict(self):
        attributes_extra = {"remote_source": self._reader.remote_source}
        return self._get_attributes() | attributes_extra

    def __hash__(self):
        # TODO: why doesn't this get inherited correctly from File.
        #  If you remove this, tests will fail with error 'un-hashable type' for all subclasses of LocalTrack.
        #  LocalTrack should be inheriting __hash__ from File superclass
        return super().__hash__()

    def __eq__(self, item: MusifyItem):
        """Paths equal if both are LocalItems, URI attributes equal if both have a URI, names equal otherwise"""
        if hasattr(item, "path"):
            return self.path == item.path
        return super().__eq__(item)

    def __copy__(self):
        """Copy object by reloading from the file object in memory"""
        if not self._reader.file.tags:  # file is not a real file, used in testing
            new = self.__class__.__new__(self.__class__)
            for key in self.__slots__:
                setattr(new, key, getattr(self, key))
            return new

        return self.__class__(file=self._reader.file, remote_wrangler=self._reader.remote_wrangler)

    def __deepcopy__(self, _: dict = None):
        """Deepcopy object by reloading from the disk"""
        # use path if file is a real file, use file object otherwise (when testing)
        file = self._reader.file if not self._reader.file.tags else self.path
        return self.__class__(file=file, remote_wrangler=self._reader.remote_wrangler)

    def __setitem__(self, key: str, value: Any):
        if not hasattr(self, key):
            raise MusifyKeyError(f"Given key is not a valid attribute of this item: {key}")

        attr = getattr(self, key)
        if isinstance(attr, property) and attr.fset is None:
            raise MusifyAttributeError(f"Cannot set values on the given key, it is protected: {key}")

        return setattr(self, key, value)

    def __or__(self, other: Track) -> Self:
        if not isinstance(other, Track):
            raise MusifyTypeError(
                f"Incorrect item given. Cannot merge with {other.__class__.__name__} as it is not a Track"
            )

        self_copy = self.__deepcopy__()
        self_copy.merge(other, tags=TrackField.ALL)
        return self_copy

    def __ior__(self, other: Track) -> Self:
        if not isinstance(other, Track):
            raise MusifyTypeError(
                f"Incorrect item given. Cannot merge with {other.__class__.__name__} as it is not a Track"
            )

        self.merge(other, tags=TrackField.ALL)
        return self
