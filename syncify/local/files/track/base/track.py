from __future__ import annotations

from abc import ABCMeta, abstractmethod
from datetime import datetime
from glob import glob
from os.path import join, splitext, exists, getmtime, getsize
from typing import Optional, List, Union, Mapping, Set, Collection

import mutagen

from syncify.local.files.file import File
from syncify.local.files.track.base.reader import TagReader
from syncify.local.files.track.base.tags import Tags, Properties
from syncify.local.files.track.base.writer import TagWriter
from syncify.utils_new.generic import PrettyPrinter


class LocalTrack(PrettyPrinter, File, TagReader, TagWriter, metaclass=ABCMeta):
    """
    Generic track object for extracting, modifying, and saving tags for a given file.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    """

    _num_sep = "/"

    @property
    @abstractmethod
    def valid_extensions(self) -> List[str]:
        """Allowed extensions in lowercase"""
        raise NotImplementedError

    @property
    def path(self):
        return self._path

    @property
    def file(self):
        return self._file

    @classmethod
    def get_filepaths(cls, library_folder: str) -> Set[str]:
        """Get all files in a given library that match this Track object's valid filetypes."""
        paths = set()

        for ext in cls.valid_extensions:
            # first glob doesn't get filenames that start with a period
            paths.update(glob(join(library_folder, "**", f"*{ext}"), recursive=True))
            # second glob only picks up filenames that start with a period
            paths.update(glob(join(library_folder, "*", "**", f".*{ext}"), recursive=True))

        return paths

    def __init__(self, file: Union[str, mutagen.File], available: Optional[Collection[str]] = None):
        self._file: Optional[mutagen.File] = None

        # all available paths for this file type
        self._available_paths: Optional[Collection[str]] = None
        # all available paths mapped as lower case to actual
        self._available_paths_lower: Optional[Mapping[str, str]] = None

        if available is not None:
            self._available_paths = set(available)
            self._available_paths_lower = {path.lower(): path for path in self._available_paths}

        if isinstance(file, str):
            self._path = file
            self.load_file()
        else:
            self._path = file.filename
            self._file = file

        if self._file is not None:
            self.load_metadata()

        self.date_added = None
        self.last_played = None
        self.play_count = None
        self.rating = None

    def load(self) -> LocalTrack:
        """General method for loading file and its metadata"""
        self.load_file()
        if self._file is not None:
            self.load_metadata()
        return self

    def load_file(self) -> Optional[mutagen.File]:
        # extract file extension and confirm file type is listed in accepted file types list
        self._validate_type(self.path)

        if self._available_paths is not None and self._path not in self._available_paths:
            # attempt to correct case-insensitive path to case-sensitive
            path = self._available_paths_lower.get(self._path.lower())
            if path is not None and exists(path):
                self._path = path

        if not exists(self._path):
            raise FileNotFoundError(f"File not found | {self._path}")

        self._file = mutagen.File(self._path)
        self.ext = splitext(self._path)[1].lower()

    def load_metadata(self) -> LocalTrack:
        """General method for extracting metadata from loaded file"""
        if self._file is not None:
            self._read_metadata()
        return self

    def save_file(self) -> bool:
        """
        Save current tags to file and update object attributes relating to file properties.

        :return: True if successful, False otherwise.
        """
        try:
            self._file.save()
            self.size = getsize(self.path)
            self.date_modified = datetime.fromtimestamp(getmtime(self.path))
        except mutagen.MutagenError as ex:
            raise ex
        return True

    def as_dict(self) -> Mapping[str, object]:
        """
        Return a dictionary representation of the tags for this track.

        :return: Dictionary of tags.
        """
        return {
            tag_name: getattr(self, tag_name, None)
            for tag_name in list(Tags.__annotations__) + list(Properties.__annotations__)
        }

    def __copy__(self):
        """Copy Track object by reloading from the file object in memory"""
        return self.__class__(file=self.file)

    def __deepcopy__(self, memodict: dict = None):
        """Deepcopy Track object by reloading from the disk"""
        return self.__class__(file=self.path)
