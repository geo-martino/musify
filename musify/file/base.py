"""
Generic base classes and functions for file operations.
"""
from abc import ABCMeta, abstractmethod
from collections.abc import Hashable
from datetime import datetime
from glob import glob
from os.path import splitext, basename, dirname, getsize, getmtime, getctime, exists, join
from typing import Any

from musify.file.exception import InvalidFileType, FileDoesNotExistError


class File(Hashable, metaclass=ABCMeta):
    """Generic class for representing a file on a system."""

    #: Extensions of files that can be loaded by this class.
    valid_extensions: frozenset[str]

    @property
    @abstractmethod
    def path(self) -> str:
        """The path to the file."""
        raise NotImplementedError

    @property
    def folder(self) -> str:
        """The parent folder of the file."""
        return basename(dirname(self.path))

    @property
    def filename(self) -> str:
        """The filename without extension."""
        return splitext(basename(self.path))[0]

    @property
    def ext(self) -> str:
        """The file extension in lowercase."""
        return splitext(self.path)[1].lower()

    @property
    def size(self) -> int | None:
        """The size of the file in bytes"""
        return getsize(self.path) if exists(self.path) else None

    @property
    def date_created(self) -> datetime | None:
        """:py:class:`datetime` object representing when the file was created"""
        return datetime.fromtimestamp(getctime(self.path)) if exists(self.path) else None

    @property
    def date_modified(self) -> datetime | None:
        """:py:class:`datetime` object representing when the file was last modified"""
        return datetime.fromtimestamp(getmtime(self.path)) if exists(self.path) else None

    @classmethod
    def _validate_type(cls, path: str) -> None:
        """Raises an exception if the ``path`` extension is not accepted"""
        ext = splitext(path)[1].casefold()
        if ext not in cls.valid_extensions:
            raise InvalidFileType(
                ext,
                f"Not an accepted {cls.__name__} file extension. "
                f"Use only: {', '.join(cls.valid_extensions)}"
            )

    @staticmethod
    def _validate_existence(path: str):
        """Raises an exception if there is no file at the given ``path``"""
        if not path or not exists(path):
            raise FileDoesNotExistError(f"File not found | {path}")

    @classmethod
    def get_filepaths(cls, folder: str) -> set[str]:
        """Get all files in a given folder that match this File object's valid filetypes recursively."""
        paths: set[str] = set()

        for ext in cls.valid_extensions:
            paths |= set(glob(join(folder, "**", f"*{ext}"), recursive=True, include_hidden=True))

        # do not return paths in the recycle bin in Windows-based folders
        return {path for path in paths if "$RECYCLE.BIN" not in path}

    @abstractmethod
    def load(self, *args, **kwargs) -> Any:
        """Load the file to this object"""
        raise NotImplementedError

    @abstractmethod
    def save(self, dry_run: bool = True, *args, **kwargs) -> Any:
        """
        Save this object to file.

        :param dry_run: Run function, but do not modify the file on the disk.
        """
        raise NotImplementedError

    def __hash__(self):
        """Uniqueness of a file is its path"""
        return hash(self.path)
