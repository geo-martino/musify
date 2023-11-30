import os
from abc import ABCMeta
from collections.abc import Mapping, Iterable
from glob import glob
from os.path import join, exists, dirname
from typing import Self

import mutagen

from syncify.abstract.item import Track, TrackProperties
from syncify.local.file import File
from .writer import TagWriter


class _MutagenMock(mutagen.FileType):
    class _MutagenInfoMock(mutagen.StreamInfo):
        def __init__(self):
            self.length = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.info = self._MutagenInfoMock()
        self.pictures = []


class LocalTrack(TagWriter, metaclass=ABCMeta):
    """
    Generic track object for extracting, modifying, and saving tags for a given file.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    """

    @property
    def file(self):
        return self._file

    @property
    def path(self):
        return self._path

    @classmethod
    def get_filepaths(cls, library_folder: str) -> set[str]:
        """Get all files in a given library that match this Track object's valid filetypes."""
        paths = set()

        # noinspection PyTypeChecker
        for ext in cls.valid_extensions:
            # first glob doesn't get filenames that start with a period
            paths |= set(glob(join(library_folder, "**", f"*{ext}"), recursive=True))
            # second glob only picks up filenames that start with a period
            paths |= set(glob(join(library_folder, "*", "**", f".*{ext}"), recursive=True))

        return paths

    def __init__(self, file: str | mutagen.FileType, available: Iterable[str] | None = None):
        super().__init__()

        # all available paths for this file type
        self._available_paths = set(available) if available is not None else None

        # all available paths mapped as lower case to actual
        self._available_paths_lower: Mapping[str, str] | None = None
        if available is not None:
            self._available_paths_lower = {path.casefold(): path for path in self._available_paths}

        if isinstance(file, str):
            self._path = file
            self._file: mutagen.FileType = self.get_file()
        else:
            self._path = file.filename
            self._file: mutagen.FileType = file

        self.load_metadata()

    def load(self) -> Self:
        """General method for loading file and its metadata"""
        self._file = self.get_file()
        self.load_metadata()
        return self

    def get_file(self) -> mutagen.FileType:
        # extract file extension and confirm file type is listed in accepted file types list
        self._validate_type(self.path)

        if self._available_paths is not None and self._path not in self._available_paths:
            # attempt to correct case-insensitive path to case-sensitive
            path = self._available_paths_lower.get(self._path.casefold())
            if path is not None and exists(path):
                self._path = path

        if not exists(self._path):
            raise FileNotFoundError(f"File not found | {self._path}")

        return mutagen.File(self._path)

    def extract_images_to_file(self, output_folder: str) -> int:
        """Extract and save all embedded images from file. Returns the number of images extracted."""
        images = self._read_images()
        if images is None:
            return False
        count = 0

        for i, image in enumerate(images):
            output_path = join(output_folder, self.filename + f"_{str(i).zfill(2)}" + image.format.casefold())
            if not exists(dirname(output_path)):
                os.makedirs(dirname(output_path))

            image.save(output_path)
            count += 1

        return count

    def as_dict(self):
        """Return a dictionary representation of the tags for this track."""
        other_attrs = {k: getattr(self, k, None) for k in ["uri", "has_uri"]}
        other_attrs = {k: getattr(self, k, None) for k in File.__dict__.keys()
                       if not k.startswith("_") and k != "valid_extensions"} | other_attrs
        other_attrs = {k: getattr(self, k, None) for k in TrackProperties.__dict__.keys()
                       if not k.startswith("_")} | other_attrs
        return {k: getattr(self, k) for k in Track.__dict__.keys() if not k.startswith("_")} | other_attrs

    def __hash__(self):
        """Uniqueness of an item is its URI + path"""
        return hash((self.uri, self.path))

    def __eq__(self, item):
        """URI attributes equal if at least one item has a URI, paths equal otherwise"""
        if hasattr(item, "path"):
            return self.path == item.path
        elif self.has_uri or item.has_uri:
            return self.has_uri == item.has_uri and self.uri == item.uri
        else:
            return self.name == self.name

    def __copy__(self):
        """
        Copy Track object by reloading from the file object in memory
        If current object has no file object present, generated new class and shallow copy attributes
        (as used for testing purposes).
        """
        if isinstance(self.file, _MutagenMock):
            obj = self.__class__.__new__(self.__class__)
            for k, v in self.__dict__.items():
                setattr(obj, k, v)
            return obj
        else:
            return self.__class__(file=self.file)

    def __deepcopy__(self, _: dict = None):
        """Deepcopy Track object by reloading from the disk"""
        return self.__class__(file=self.path)
