from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from http.client import HTTPResponse
from io import BytesIO
from os.path import splitext, basename, dirname, getsize, getmtime, getctime, exists
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen, Request

from PIL import Image, UnidentifiedImageError

from syncify.local.exception import InvalidFileType, ImageLoadError


class File(metaclass=ABCMeta):
    """Generic class for representing a file on a system."""

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
        return splitext(self.path)[1].casefold()

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

    @property
    @abstractmethod
    def valid_extensions(self) -> frozenset[str]:
        """Allowed extensions in lowercase"""
        raise NotImplementedError

    def _validate_type(self, path: str) -> None:
        """Raises exception if the path's extension is not accepted"""
        ext = splitext(path)[1].casefold()
        if ext not in self.valid_extensions:
            raise InvalidFileType(
                ext,
                f"Not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.valid_extensions)}"
            )

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


@dataclass(frozen=True)
class TagMap:
    """Map of human-friendly tag name to ID3 tag ids for a given file type"""

    title: list[str]
    artist: list[str]
    album: list[str]
    album_artist: list[str]
    track_number: list[str]
    track_total: list[str]
    genres: list[str]
    year: list[str]
    bpm: list[str]
    key: list[str]
    disc_number: list[str]
    disc_total: list[str]
    compilation: list[str]
    comments: list[str]
    images: list[str]

    def __getitem__(self, key: str) -> list[str]:
        """Safely get the value of a given attribute key, returning an empty string if the key is not found"""
        return getattr(self, key, [])


def get_image_bytes(image: Image.Image) -> bytes:
    """Extracts bytes from a given Image file"""
    image_bytes_arr = BytesIO()
    image.save(image_bytes_arr, format=image.format)
    return image_bytes_arr.getvalue()
