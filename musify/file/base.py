"""
Generic base classes and functions for file operations.
"""
from abc import ABCMeta, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from musify.file.exception import InvalidFileType, FileDoesNotExistError


class File(metaclass=ABCMeta):
    """Generic class for representing a file on a system."""

    __slots__ = ()

    #: Extensions of files that can be loaded by this class.
    valid_extensions: frozenset[str]

    @property
    @abstractmethod
    def path(self) -> Path:
        """The path to the file."""
        raise NotImplementedError

    @property
    def folder(self) -> str:
        """The parent folder of the file."""
        return self.path.parent.name

    @property
    def filename(self) -> str:
        """The filename without extension."""
        return self.path.stem

    @property
    def ext(self) -> str:
        """The file extension in lowercase."""
        return self.path.suffix

    @property
    def size(self) -> int | None:
        """The size of the file in bytes"""
        return self.path.stat().st_size if self.path.is_file() else None

    @property
    def date_created(self) -> datetime | None:
        """:py:class:`datetime` object representing when the file was created"""
        return datetime.fromtimestamp(self.path.stat().st_ctime) if self.path.is_file() else None

    @property
    def date_modified(self) -> datetime | None:
        """:py:class:`datetime` object representing when the file was last modified"""
        return datetime.fromtimestamp(self.path.stat().st_mtime) if self.path.is_file() else None

    @classmethod
    def _validate_type(cls, path: Path) -> None:
        """Raises an exception if the ``path`` extension is not accepted"""
        if path.suffix not in cls.valid_extensions:
            raise InvalidFileType(
                path.suffix,
                f"Not an accepted {cls.__name__} file extension. "
                f"Use only: {', '.join(cls.valid_extensions)}"
            )

    @staticmethod
    def _validate_existence(path: Path):
        """Raises an exception if there is no file at the given ``path``"""
        if not path.is_file():
            raise FileDoesNotExistError(path)

    @classmethod
    def get_filepaths(cls, folder: str | Path) -> set[Path]:
        """Get all files in a given folder that match this File object's valid filetypes recursively."""
        paths: set[Path] = set()
        folder = Path(folder)

        for ext in cls.valid_extensions:
            paths |= set(folder.rglob(str(Path("**", f"[!.]*{ext}"))))
            # paths |= set(folder.rglob(str(Path("**", f".*{ext}"))))

        # do not return paths in the recycle bin in Windows-based folders
        return {path for path in paths if "$RECYCLE.BIN" not in path.parts}

    @abstractmethod
    async def load(self, *args, **kwargs) -> Any:
        """Load the file to this object"""
        raise NotImplementedError

    @abstractmethod
    async def save(self, dry_run: bool = True, *args, **kwargs) -> Any:
        """
        Save this object to file.

        :param dry_run: Run function, but do not modify the file on the disk.
        """
        raise NotImplementedError

    def __hash__(self):
        """Uniqueness of a file is its path"""
        return hash(self.path)
