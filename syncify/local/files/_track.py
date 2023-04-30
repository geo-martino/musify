from __future__ import annotations

from abc import ABC
from datetime import datetime
from glob import glob
from os.path import join, splitext, exists
from typing import Optional, List, Union, Mapping, MutableMapping

import mutagen

from syncify.local.files.tags.extract import TagExtractor
from syncify.local.files.tags.helpers import Tags, Properties
from syncify.local.files.tags.update import TagUpdater
from syncify.utils.logger import Logger


class Track(ABC, TagExtractor, TagUpdater):

    _num_sep = "/"
    _unavailable_uri_value = "spotify:track:unavailable"

    filetypes: List[str] = None  # allowed extensions in lowercase
    _filepaths: List[str] = None  # all file paths in library
    _filepaths_lower: List[str] = None  # all file paths in library in lowercase

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Logger.__init__(self)

        self.valid: bool = False
        self.position: Optional[int] = position
        self._file: Optional[mutagen.File] = None

        if isinstance(file, str):
            self.path = file
            self.load_file()
        else:
            self.path = file.filename
            self.file = file

        if self._file is not None:
            self.load_metadata()

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def file(self):
        return self._file

    @file.setter
    def file(self, value):
        self._file = value

    @classmethod
    def set_file_paths(cls, music_folder: str) -> None:
        """Set class property for all available file paths. Necessary for loading with case-sensitive logic."""
        cls._filepaths = []
        for ext in cls.filetypes:
            # first glob doesn't get filenames that start with a period
            cls._filepaths += glob(join(music_folder, "**", f"*{ext}"), recursive=True)
            # second glob only picks up filenames that start with a period
            cls._filepaths += glob(join(music_folder, "*", "**", f".*{ext}"), recursive=True)

        cls._filepaths.sort()
        cls._filepaths_lower = [path.lower() for path in cls._filepaths]

    def _get_case_sensitive_path(self, path: str) -> str:
        """
        Try to find a case-sensitive path from the list of available paths.

        :returns: Case-sensitive path if found
        :raises: FileNotFoundError. If there are no available file paths or a case-sensitive path cannot be found.
        """
        if len(self._filepaths) != len(self._filepaths_lower):
            raise AssertionError("Number of paths in file path lists does not match")

        try:
            return self._filepaths[self._filepaths_lower.index(path.lower())]
        except (ValueError, TypeError):
            raise FileNotFoundError(f"Path not found in library: {path}")

    def load(self) -> Track:
        """
        General method for loading file and metadata from a track,

        :returns: self.
        """
        self.load_file()
        if self._file is not None:
            self.load_metadata()
        return self

    def load_file(self) -> Optional[mutagen.File]:
        self.valid = False

        # extract file extension and confirm file type is listed in accepted file types list
        ext = splitext(self.path)[1].lower()
        if ext not in self.filetypes:
            self._logger.warning(
                f"{ext} not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.filetypes)}")
            return

        if self._filepaths is not None and self._path not in self._filepaths:
            # correct case-insensitive path to case-sensitive
            path = self._get_case_sensitive_path(self._path)
            if not exists(path):
                self._logger.error(f"File not found | {self._path}")
                return

            self._path = path
        elif not exists(self._path):
            self._logger.error(f"File not found | {self._path}")
            return

        self._file = mutagen.File(self.path)
        self.ext = ext

    def load_metadata(self) -> Track:
        """
        General method for extracting metadata from loaded file and declaring track object valid

        :returns: self.
        """
        self.valid = False

        if self._file is not None:
            self._extract_metadata()
            self.valid = True

        return self

    def save_file(self) -> bool:
        """
        Save current mutagen tags to file

        :return: True if successful, False otherwise.
        """
        try:
            self._file.save()
        except Exception:
            return False
        return True

    def as_dict(self) -> Mapping[str, object]:
        """
        Return the tags of this track as a dictionary.

        :return: Dictionary of tags.
        """
        return {
            tag_name: getattr(self, tag_name, None)
            for tag_name in ["position"] + list(Tags.__annotations__) + list(Properties.__annotations__)
        }

    def as_json(self) -> Mapping[str, object]:
        """
        Return the tags of this track as a dictionary formatted as JSON.

        :return: JSON-formatted dictionary of tags.
        """
        tags = {}

        for tag_name, tag_value in self.as_dict().items():
            if isinstance(tag_value, datetime):
                tags[tag_name] = tag_value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                tags[tag_name] = tag_value

        return tags

    def __repr__(self) -> str:
        result = f"{self.__class__.__name__}(\n{{}}\n)"
        tags: MutableMapping[str, object] = {"valid": self.valid}
        tags.update(self.as_dict())

        max_width = max(len(tag_name) for tag_name in tags)
        tags_repr = []
        for tag_name, tag_value in tags.items():
            tags_repr.append(f"{tag_name : <{max_width}} = {repr(tag_value)}")

        indent = 2
        return result.format("\n".join([" " * indent + tag for tag in tags_repr]))

    def __str__(self) -> str:
        return repr(self)

    def __copy__(self):
        """Copy Track object by generating new Track from the currently loaded file"""
        cls = self.__class__
        return cls(file=self.file, position=self.position)

    def __deepcopy__(self, memodict: dict = None):
        """Deepcopy Track object by generating new Track from the current path"""
        cls = self.__class__
        return cls(file=self.path, position=self.position)

