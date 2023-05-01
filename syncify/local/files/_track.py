from __future__ import annotations

from abc import ABC
from datetime import datetime
from glob import glob
from os.path import join, splitext, exists
from typing import Optional, List, Union, Mapping, MutableMapping, Set

import mutagen

from syncify.local.files.tags.exception import IllegalFileTypeError
from syncify.local.files.tags.extract import TagExtractor
from syncify.local.files.tags.helpers import Tags, Properties
from syncify.local.files.tags.update import TagUpdater
from syncify.utils.logger import Logger


class Track(ABC, TagExtractor, TagUpdater):

    _num_sep = "/"

    filetypes: List[str] = None  # allowed extensions in lowercase
    filepaths: Set[str] = None  # all file paths in library for this file type
    _filepaths_lower_map: Mapping[str, str] = None  # all file paths in library mapped as lower case to actual

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        """
        :param file: The path or Mutagen object of the file to load.
        :param position: A position to assign to this track e.g. for playlist order.
        """
        Logger.__init__(self)

        self.valid: bool = False
        self.position = None
        self._file: Optional[mutagen.File] = None

        if isinstance(file, str):
            self._path = file
            self.load_file()
        else:
            self._path = file.filename
            self._file = file

        if self._file is not None:
            self.load_metadata(position=position)

        self.date_added = None
        self.last_played = None
        self.play_count = None
        self.rating = None

    @property
    def path(self):
        return self._path

    @property
    def file(self):
        return self._file

    @classmethod
    def set_file_paths(cls, library_folder: str) -> None:
        """
        Set class property for all available file paths. Necessary for loading with case-sensitive logic.

        :param library_folder: Path of the music library to search.
        """
        cls.filepaths = set()
        for ext in cls.filetypes:
            # first glob doesn't get filenames that start with a period
            cls.filepaths.update(glob(join(library_folder, "**", f"*{ext}"), recursive=True))
            # second glob only picks up filenames that start with a period
            cls.filepaths.update(glob(join(library_folder, "*", "**", f".*{ext}"), recursive=True))

        cls._filepaths_lower_map = {path.lower(): path for path in cls.filepaths}

    def load(self, position: Optional[int] = None) -> Track:
        """
        General method for loading file and metadata from a track,

        :param position: A position to assign to this track e.g. for playlist order.
        :returns: self.
        """
        self.load_file()
        if self._file is not None:
            self.load_metadata(position=position if position is not None else self.position)
        return self

    def load_file(self) -> Optional[mutagen.File]:
        self.valid = False

        # extract file extension and confirm file type is listed in accepted file types list
        ext = splitext(self.path)[1].lower()
        if ext not in self.filetypes:
            raise IllegalFileTypeError(
                ext,
                f"Not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.filetypes)}"
            )

        if self.filepaths is not None and self._path not in self.filepaths:
            # attempt to correct case-insensitive path to case-sensitive
            path = self._filepaths_lower_map.get(self._path.lower())
            if path is not None and exists(path):
                self._path = path

        if not exists(self._path):
            raise FileNotFoundError(f"File not found | {self._path}")

        self._file = mutagen.File(self._path)
        self.ext = ext

    def load_metadata(self, position: Optional[int] = None) -> Track:
        """
        General method for extracting metadata from loaded file and declaring track object valid

        :param position: A position to assign to this track e.g. for playlist order.
        :returns: self.
        """
        self.valid = False

        if self._file is not None:
            self._extract_metadata(position=position if position is not None else self.position)
            self.valid = True

        return self

    def save_file(self) -> bool:
        """
        Save current mutagen tags to file

        :return: True if successful, False otherwise.
        """
        try:
            self._file.save()
        except mutagen.MutagenError as ex:
            raise ex
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
        """Copy Track object by reloading from the file object in memory"""
        return self.__class__(file=self.file, position=self.position)

    def __deepcopy__(self, memodict: dict = None):
        """Deepcopy Track object by reloading from the disk"""
        return self.__class__(file=self.path, position=self.position)
