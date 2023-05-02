from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from glob import glob
from os.path import join, splitext, exists
from typing import Optional, List, Union, Mapping, Set

import mutagen

from syncify.local.files.track.reader import TagReader
from syncify.local.files.track.writer import TagWriter
from syncify.local.files.track.tags import Tags, Properties
from syncify.local.files.utils.exception import IllegalFileTypeError


class Track(ABC, TagReader, TagWriter):
    """
    Generic track object for extracting, modifying, and saving tags for a given file.

    :param file: The path or Mutagen object of the file to load.
    """

    _num_sep = "/"

    available_track_paths: Set[str] = None  # all available paths for this file type
    _available_track_paths_lower_map: Mapping[str, str] = None  # all available paths mapped as lower case to actual

    @property
    @abstractmethod
    def track_ext(self) -> List[str]:
        """Allowed extensions in lowercase"""
        raise NotImplementedError

    @property
    def path(self):
        return self._path

    @property
    def file(self):
        return self._file

    @classmethod
    def set_file_paths(cls, library_folder: str) -> None:
        """
        Set class property for all available track file paths. Necessary for loading with case-sensitive logic.

        :param library_folder: Path of the music library to search.
        """
        if cls.available_track_paths is None:
            cls.available_track_paths = set()

        for ext in cls.track_ext:
            # first glob doesn't get filenames that start with a period
            cls.available_track_paths.update(glob(join(library_folder, "**", f"*{ext}"), recursive=True))
            # second glob only picks up filenames that start with a period
            cls.available_track_paths.update(glob(join(library_folder, "*", "**", f".*{ext}"), recursive=True))

        cls._available_track_paths_lower_map = {path.lower(): path for path in cls.available_track_paths}

    def __init__(self, file: Union[str, mutagen.File]):
        self._file: Optional[mutagen.File] = None

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

    def load(self) -> Track:
        """General method for loading file and its metadata"""
        self.load_file()
        if self._file is not None:
            self.load_metadata()
        return self

    def load_file(self) -> Optional[mutagen.File]:
        # extract file extension and confirm file type is listed in accepted file types list
        ext = splitext(self.path)[1].lower()
        if ext not in self.track_ext:
            raise IllegalFileTypeError(
                ext,
                f"Not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.track_ext)}"
            )

        if self.available_track_paths is not None and self._path not in self.available_track_paths:
            # attempt to correct case-insensitive path to case-sensitive
            path = self._available_track_paths_lower_map.get(self._path.lower())
            if path is not None and exists(path):
                self._path = path

        if not exists(self._path):
            raise FileNotFoundError(f"File not found | {self._path}")

        self._file = mutagen.File(self._path)
        self.ext = ext

    def load_metadata(self) -> Track:
        """General method for extracting metadata from loaded file"""
        if self._file is not None:
            self._read_metadata()
        return self

    def save_file(self) -> bool:
        """
        Save current tags to file

        :return: True if successful, False otherwise.
        """
        try:
            self._file.save()
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

    def as_json(self) -> Mapping[str, object]:
        """
        Return a dictionary representation of the tags for this track that is safe to output to json.

        :return: JSON-formatted dictionary of tags.
        """
        tags = {}

        for tag_name, tag_value in self.as_dict().items():
            if isinstance(tag_value, datetime):
                tags[tag_name] = tag_value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                tags[tag_name] = tag_value

        return tags

    def __str__(self) -> str:
        result = f"{self.__class__.__name__}(\n{{}}\n)"
        tags = self.as_dict()
        indent = 2

        max_width = max(len(tag_name) for tag_name in tags)
        tags_repr = []
        for tag_name, tag_value in tags.items():
            tags_repr.append(f"{tag_name : <{max_width}} = {repr(tag_value)}")

        return result.format("\n".join([" " * indent + tag for tag in tags_repr]))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.as_dict()})"

    def __copy__(self):
        """Copy Track object by reloading from the file object in memory"""
        return self.__class__(file=self.file)

    def __deepcopy__(self, memodict: dict = None):
        """Deepcopy Track object by reloading from the disk"""
        return self.__class__(file=self.path)
