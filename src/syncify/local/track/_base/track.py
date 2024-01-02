import inspect
import os
from abc import ABCMeta
from collections.abc import Mapping, Iterable
from copy import deepcopy
from glob import glob
from os.path import join, exists, dirname
from typing import Any, Self

import mutagen

from syncify.abstract import Item
from syncify.abstract.object import Track
from syncify.fields import TrackField
from syncify.local._file import File
from syncify.local.exception import FileDoesNotExistError
from syncify.local.track._base.reader import TagReader
from syncify.local.track._base.writer import TagWriter
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitIterable


class LocalTrack(TagWriter, metaclass=ABCMeta):
    """
    Generic track object for extracting, modifying, and saving tags for a given file.

    :ivar uri_tag: The tag field to use as the URI tag in the file's metadata.
    :ivar num_sep: Some number values come as a combined string i.e. track number/track total
        Define the separator to use when representing both values as a combined string.
    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    """

    __slots__ = ("_file", "_available_paths", "_available_paths_lower")

    @property
    def file(self):
        return self._file

    @classmethod
    def get_filepaths(cls, library_folder: str) -> set[str]:
        """Get all files in a given library that match this Track object's valid filetypes."""
        paths = set()

        for ext in cls.valid_extensions:
            # first glob doesn't get filenames that start with a period
            paths |= set(glob(join(library_folder, "**", f"*{ext}"), recursive=True))
            # second glob only picks up filenames that start with a period
            paths |= set(glob(join(library_folder, "*", "**", f".*{ext}"), recursive=True))

        return paths

    def __init__(
            self,
            file: str | mutagen.FileType,
            available: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        super().__init__(remote_wrangler=remote_wrangler)

        # all available paths for this file type
        self._available_paths = set(available)
        # all available paths mapped as lower case to actual
        self._available_paths_lower: Mapping[str, str] = {path.casefold(): path for path in self._available_paths}

        self._file: mutagen.FileType = self.load(file) if isinstance(file, str) else file
        self.load_metadata()

    def load(self, path: str | None = None) -> mutagen.FileType:
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

        if self._available_paths and path not in self._available_paths:
            # attempt to correct case-insensitive path to case-sensitive
            path_sys = self._available_paths_lower.get(path.casefold())
            if path_sys is not None and exists(path_sys):
                path = path_sys

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
            output_path = join(output_folder, self.filename + f"_{str(i).zfill(2)}" + image.format.casefold())
            os.makedirs(dirname(output_path), exist_ok=True)

            image.save(output_path)
            count += 1

        return count

    def as_dict(self):
        """Return a dictionary representation of the tags for this track."""
        exclude = {
            inspect.currentframe().f_code.co_name,
            "name",
            "valid_extensions",
            "load",
            "save",
            "remote_wrangler",
            "_clean_tags",
            "_available_paths",
            "_available_paths_lower",
            "_file",
        }

        # manually prep attributes in specific order according to parent classes
        attributes_core = {
            k: getattr(self, k) for k in Track.__dict__.keys() if not k.startswith("_") and k not in exclude
        }
        attributes_uri = {k: getattr(self, k) for k in Item.__dict__.keys() if "uri" in k}
        attributes_uri["remote_source"] = self.remote_wrangler.source if self.remote_wrangler else None
        attributes_file = {
            k: getattr(self, k) for k in File.__dict__.keys() if not k.startswith("_") and k not in exclude
        }
        attributes = attributes_core | attributes_uri | attributes_file
        attributes_other = {
            k.lstrip("_"): getattr(self, k) for k in self.__dict__.keys()
            if k not in exclude and k.lstrip("_") not in attributes
        }

        return attributes | attributes_other

    def __hash__(self):  # TODO: why doesn't this get inherited correctly from File
        return super().__hash__()

    def __eq__(self, item: Item):
        """Paths equal if both are LocalItems, URI attributes equal if both have a URI, names equal otherwise"""
        if hasattr(item, "path"):
            return self.path == item.path
        elif self.has_uri and item.has_uri:
            return self.uri == item.uri
        return self.name == item.name

    def __copy__(self):
        """Copy object by reloading from the file object in memory"""
        if not self.file.tags:  # file is not a real file, used in testing
            obj = self.__class__.__new__(self.__class__)
            for key in TagReader.__slots__:
                setattr(obj, key, getattr(self, key))
            for key in self.__slots__:
                setattr(obj, key, getattr(self, key))
            return obj
        return self.__class__(file=self.file, available=self._available_paths, remote_wrangler=self.remote_wrangler)

    def __deepcopy__(self, _: dict = None):
        """Deepcopy object by reloading from the disk"""
        # use path if file is a real file, use file object otherwise (when testing)
        file = self.file if not self.file.tags else self.path
        return self.__class__(file=file, available=self._available_paths, remote_wrangler=self.remote_wrangler)

    def __setitem__(self, key: str, value: Any):
        if not hasattr(self, key):
            raise KeyError(f"Given key is not a valid attribute of this item: {key}")

        attr = getattr(self, key)
        if isinstance(attr, property) and attr.fset is None:
            raise AttributeError(f"Cannot values on the given key, it is protected: {key}")

        return setattr(self, key, value)

    def __or__(self, other: Track) -> Self:
        if not isinstance(other, Track):
            raise TypeError(
                f"Incorrect item given. Cannot merge with {other.__class__.__name__} as it is not a Track"
            )

        self_copy = self.__deepcopy__()
        self_copy.merge(other, tags=TrackField.ALL)
        return self_copy

    def __ior__(self, other: Track) -> Self:
        if not isinstance(other, Track):
            raise TypeError(
                f"Incorrect item given. Cannot merge with {other.__class__.__name__} as it is not a Track"
            )

        self.merge(other, tags=TrackField.ALL)
        return self
