"""
Generic file operations. Base class for generic File and functions for reading/writing basic file types.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Hashable, Collection, Iterable
from datetime import datetime
from glob import glob
from http.client import HTTPResponse
from io import BytesIO
from os import sep
from os.path import splitext, basename, dirname, getsize, getmtime, getctime, exists, join
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen, Request

from PIL import Image, UnidentifiedImageError

from musify.local.exception import InvalidFileType, ImageLoadError
from musify.shared.core.misc import PrettyPrinter


def open_image(source: str | bytes | Path | Request) -> Image.Image:
    """
    Open Image object from a given URL or file path

    :return: The loaded :py:class:`Image.Image`
    :raise ImageLoadError: If the image cannot be loaded.
    """

    try:  # open image from link
        if isinstance(source, Request) or (isinstance(source, str) and source.startswith("http")):
            response: HTTPResponse = urlopen(source)
            image = Image.open(response)
            response.close()
            return image

        elif not isinstance(source, Request):
            return Image.open(source)

    except (URLError, FileNotFoundError, UnidentifiedImageError):
        pass
    raise ImageLoadError(f"{source} | Failed to open image")


def get_image_bytes(image: Image.Image) -> bytes:
    """Extracts bytes from a given Image file"""
    image_bytes_arr = BytesIO()
    image.save(image_bytes_arr, format=image.format)
    return image_bytes_arr.getvalue()


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

    def _validate_type(self, path: str) -> None:
        """Raises exception if the path's extension is not accepted"""
        ext = splitext(path)[1].casefold()
        if ext not in self.valid_extensions:
            raise InvalidFileType(
                ext,
                f"Not an accepted {self.__class__.__name__} file extension. "
                f"Use only: {', '.join(self.valid_extensions)}"
            )

    @classmethod
    def get_filepaths(cls, folder: str) -> set[str]:
        """Get all files in a given folder that match this File object's valid filetypes recursively."""
        paths = set()

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

        :param dry_run: Run function, but do not modify file at all.
        """
        raise NotImplementedError

    def __hash__(self):
        """Uniqueness of a file is its path"""
        return hash(self.path)


class PathMapper(PrettyPrinter):
    """
    Simple path mapper which extracts paths from :py:class:`File` objects.
    Can be extended by child classes for more complex mapping operations.
    """

    def map(self, value: str | File | None, check_existence: bool = False) -> str | None:
        """
        Map the given ``value`` by either extracting the path from a :py:class:`File` object,
        or returning the ``value`` as is, assuming it is a string.

        :param value: The value to extract a path from.
        :param check_existence: When True, check the path exists before returning it. If it doesn't exist, returns None.
        :return: The path if ``check_existence`` is False, or if ``check_existence`` is True and path exists,
            None otherwise.
        """
        path = value.path if isinstance(value, File) else value
        if not check_existence or exists(path):
            return path

    def map_many(self, values: Collection[str | File | None], check_existence: bool = False) -> list[str]:
        """Run :py:meth:`map` operation on many ``values`` only returning those values that are not None or empty."""
        paths = [self.map(value=value, check_existence=check_existence) for value in values]
        return [path for path in paths if path]

    def unmap(self, value: str | File | None, check_existence: bool = False) -> str | None:
        """
        Map the given ``value`` by either extracting the path from a :py:class:`File` object,
        or returning the ``value`` as is, assuming it is a string.

        :param value: The value to extract a path from.
        :param check_existence: When True, check the path exists before returning it. If it doesn't exist, returns None.
        :return: The path if ``check_existence`` is False, or if ``check_existence`` is True and path exists,
            None otherwise.
        """
        path = value.path if isinstance(value, File) else value
        if not check_existence or exists(path):
            return path

    def unmap_many(self, values: Collection[str | File | None], check_existence: bool = False) -> list[str]:
        """Run :py:meth:`unmap` operation on many ``values`` only returning those values that are not None or empty."""
        paths = [self.unmap(value=value, check_existence=check_existence) for value in values]
        return [path for path in paths if path]

    def as_dict(self) -> dict[str, Any]:
        return {}


class PathStemMapper(PathMapper):
    """
    A more complex path mapper which attempts to replace the stems of paths from strings and :py:class:`File` objects.
    Plus, attempts to case-correct paths.

    Useful for cross-platform support. Can be used to correct paths if the same file exists in
    different locations according to different mounts and/or multiple operating systems.
    """

    __slots__ = ("_stem_map", "_stem_unmap", "_available_paths")

    @property
    def available_paths(self) -> dict[str, str]:
        """
        A map of the available paths stored in this object. Simply ``{<lower-case path>: <correctly-cased path>}``.
        When assigning new values to this property, the stored map will update itself
        with the new values rather than overwrite.
        """
        return self._available_paths

    @available_paths.setter
    def available_paths(self, values: Iterable[str]):
        self._available_paths.update({path.casefold(): path for path in values})

    @property
    def stem_map(self) -> dict[str, str]:
        """
        A map of ``{<stem to be replaced>: <its replacement>}``.
        Assigning new values to this property updates itself
        plus the ``stem_unmap`` property with the reverse of this map.
        """
        return self._stem_map

    @stem_map.setter
    def stem_map(self, values: dict[str, str]):
        self._stem_map.update(values)
        self._stem_unmap.update({v: k for k, v in self._stem_map.items()})

    @property
    def stem_unmap(self) -> dict[str, str]:
        """
        A map of ``{<replacement stems>: <stem to be replaced>}`` i.e. just the opposite map of ``stem_map``.
        Assign new values to ``stem_map`` to update.
        """
        return self._stem_unmap

    def __init__(self, stem_map: dict[str, str] | None = None, available_paths: Iterable[str] = ()):
        self._stem_map: dict[str, str] = {}
        self._stem_unmap: dict[str, str] = {}
        self._available_paths: dict[str, str] = {}

        self.stem_map = stem_map or {}
        self.available_paths = available_paths

    def map(self, value: str | File | None, check_existence: bool = False) -> str | None:
        """
        Map the given value by replacing its stem according to stored ``stem_map``,
        correcting path separators according to the separators of the replacement stem,
        and case correcting path from stored ``available_paths``.

        :param value: The value to map.
        :param check_existence: When True, check the path exists before returning it. If it doesn't exist, returns None.
        :return: The path if ``check_existence`` is False, or if ``check_existence`` is True and path exists,
            None otherwise.
        """
        path = value.path if isinstance(value, File) else value

        seps = ()
        for stem, replacement in self.stem_map.items():
            if path.casefold().startswith(stem.casefold()):
                if "/" in replacement and "/" not in path:
                    seps = ("\\", "/")
                elif "\\" in replacement and "\\" not in path:
                    seps = ("/", "\\")
                path = sep.join([replacement.rstrip("\\/"), path[len(stem):].lstrip("\\/")]).rstrip("\\/")
                break

        if sep == "\\":
            path = path.replace("\\\\", "\\")
        if seps:
            path = path.replace(*seps)

        path = self.available_paths.get(path.casefold(), path)
        if not check_existence or exists(path):
            return path

    def unmap(self, value: str | File | None, check_existence: bool = False) -> str | None:
        """
        Map the given value by replacing its stem according to stored ``stem_unmap``,
        correcting path separators according to the separators of the replacement stem,
        and case correcting path from stored ``available_paths`` (i.e. mostly the reverse of :py:meth:`map`).

        :param value: The value to map.
        :param check_existence: When True, check the path exists before returning it. If it doesn't exist, returns None.
        :return: The path if ``check_existence`` is False, or if ``check_existence`` is True and path exists,
            None otherwise.
        """
        path = value.path if isinstance(value, File) else value

        seps = ()
        for stem, replacement in self.stem_unmap.items():
            if path.casefold().startswith(stem.casefold()):
                if "/" in replacement and "/" not in path:
                    seps = ("\\", "/")
                elif "\\" in replacement and "\\" not in path:
                    seps = ("/", "\\")
                path = sep.join([replacement.rstrip("\\/"), path[len(stem):].lstrip("\\/")])
                break

        if sep == "\\":
            path = path.replace("\\\\", "\\")
        if seps:
            path = path.replace(*seps)

        path = self.available_paths.get(path.casefold(), path)
        if not check_existence or exists(path):
            return path

    def as_dict(self) -> dict[str, Any]:
        return {
            "stem_map": self.stem_map,
            "stem_unmap": self.stem_unmap,
            "available_paths": list(self.available_paths.values())
        }
