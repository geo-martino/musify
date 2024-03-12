"""
Combines reader and writer classes for metadata/tags/properties operations on audio files.
"""

import os
from abc import ABCMeta
from copy import deepcopy
from os.path import join, exists, dirname
from typing import Any, Self

import mutagen

from musify.local.exception import FileDoesNotExistError
from musify.local.track.base.reader import TagReader
from musify.local.track.base.writer import TagWriter
from musify.shared.core.base import Item
from musify.shared.core.object import Track
from musify.shared.exception import MusifyKeyError, MusifyAttributeError, MusifyTypeError
from musify.shared.field import TrackField
from musify.shared.remote.processors.wrangle import RemoteDataWrangler
from musify.shared.types import UnitIterable


class LocalTrack[T: mutagen.FileType](TagWriter, metaclass=ABCMeta):
    """
    Generic track object for extracting, modifying, and saving metadata/tags/properties for a given file.

    :param file: The path or Mutagen object of the file to load.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    """

    __slots__ = ("_file",)
    __attributes_classes__ = TagReader

    @property
    def file(self):
        return self._file

    def __init__(self, file: str | T, remote_wrangler: RemoteDataWrangler = None):
        super().__init__(remote_wrangler=remote_wrangler)

        self._file: T = self.load(file) if isinstance(file, str) else file
        self.load_metadata()

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

    def merge(self, track: Track, tags: UnitIterable[TrackField] = TrackField.ALL) -> None:
        """Set the tags of this track equal to the given ``track``. Give a list of ``tags`` to limit which are set"""
        tag_names = TrackField.__tags__ if tags == TrackField.ALL else set(TrackField.to_tags(tags))

        for tag in tag_names:  # merge on each tag
            if hasattr(track, tag):
                setattr(self, tag, deepcopy(track[tag]))

    def extract_images_to_file(self, output_folder: str) -> int:
        """Extract and save all embedded images from file. Returns the number of images extracted."""
        images = self._read_images()
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
        attributes_extra = {"remote_source": self.remote_wrangler.source if self.remote_wrangler else None}
        return self._get_attributes() | attributes_extra

    def __hash__(self):  # TODO: why doesn't this get inherited correctly from File
        return super().__hash__()

    def __eq__(self, item: Item):
        """Paths equal if both are LocalItems, URI attributes equal if both have a URI, names equal otherwise"""
        if hasattr(item, "path"):
            return self.path == item.path
        return super().__eq__(item)

    def __copy__(self):
        """Copy object by reloading from the file object in memory"""
        if not self.file.tags:  # file is not a real file, used in testing
            obj = self.__class__.__new__(self.__class__)
            for key in TagReader.__slots__:
                setattr(obj, key, getattr(self, key))
            for key in self.__slots__:
                setattr(obj, key, getattr(self, key))
            return obj
        return self.__class__(file=self.file, remote_wrangler=self.remote_wrangler)

    def __deepcopy__(self, _: dict = None):
        """Deepcopy object by reloading from the disk"""
        # use path if file is a real file, use file object otherwise (when testing)
        file = self.file if not self.file.tags else self.path
        return self.__class__(file=file, remote_wrangler=self.remote_wrangler)

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
