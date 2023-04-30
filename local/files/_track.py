from abc import ABC
from glob import glob
from os.path import join, splitext
from typing import Optional, List, Union

import mutagen

from local.files.tags.extract import TagExtractor
from local.files.tags.update import TagUpdater
from utils.logger import Logger


class Track(ABC, Logger, TagExtractor, TagUpdater):

    _num_sep = "/"
    _unavailable_uri_value = "spotify:track:unavailable"

    filetypes: List[str] = None  # allowed extensions in lowercase
    _filepaths: List[str] = None  # all file paths in library
    _filepaths_lower: List[str] = None  # all file paths in library in lowercase

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Logger.__init__(self)

        self.valid: bool = False
        self.position: Optional[int] = position

        if isinstance(file, str):
            self.path = file
            self.load_file()
        else:
            self.path = file.filename
            self.file = file

        self.load()

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
        """
        Set class property for all available file paths. Necessary for loading with case-sensitive logic.
        """
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

    def load_file(self) -> None:
        """
        Load local file using mutagen and set object file path and extension properties.

        :returns: Mutagen file object or None if load error.
        """
        # extract file extension and confirm file type is listed in accepted file types list
        ext = splitext(self.path)[1].lower()
        if ext not in self.filetypes:
            self._logger.warning(
                f"{ext} not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.filetypes)}")
            return

        try:  # load path as given
            file = mutagen.File(self.path)
        except mutagen.MutagenError:
            try:  # load case-sensitive path and adjust object path reference if found
                path = self._get_case_sensitive_path(self.path)
                file = mutagen.File(path)
                self.path = path
            except (mutagen.MutagenError, FileNotFoundError):  # give up
                self._logger.error(f"File not found | {self.path}")
                return

        self.ext = ext
        self._file = file

    def load(self) -> None:
        """General method for extracting metadata from loaded file and declaring track object valid"""
        self.valid = False

        if self._file is not None:
            self._extract_metadata()
            self.valid = True

    def load_new(self):
        """Generate new Track object from the currently loaded file"""
        return Track(file=self.file, position=self.position)

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
