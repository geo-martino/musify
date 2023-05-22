from abc import ABCMeta, abstractmethod
from datetime import datetime
from http.client import HTTPResponse
from io import BytesIO
from os.path import splitext, basename, dirname, getsize, getmtime, getctime
from typing import List
from urllib.error import URLError
from urllib.request import urlopen

from PIL import Image, UnidentifiedImageError

from syncify.local.exception import IllegalFileTypeError, ImageLoadError


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
        return splitext(self.path)[1].lower()

    @property
    def size(self) -> int:
        """The size of the file in bytes"""
        return getsize(self.path)

    @property
    def date_created(self) -> datetime:
        """datetime object representing when the file was created"""
        return datetime.fromtimestamp(getctime(self.path))

    @property
    def date_modified(self) -> datetime:
        """datetime object representing when the file was last modified"""
        return datetime.fromtimestamp(getmtime(self.path))

    @property
    @abstractmethod
    def valid_extensions(self) -> List[str]:
        """Allowed extensions in lowercase"""
        raise NotImplementedError

    def _validate_type(self, path: str):
        """Raises exception if the path's extension is not accepted"""
        ext = splitext(path)[1].lower()
        if ext not in self.valid_extensions:
            raise IllegalFileTypeError(
                ext,
                f"Not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.valid_extensions)}")


def open_image(image_link: str) -> Image.Image:
    """
    Open Image object from a given URL or file path

    :raises ImageLoadError: If the image cannot be loaded.
    """

    try:  # open image from link
        if image_link.startswith("http"):
            response: HTTPResponse = urlopen(image_link)
            image = Image.open(response)
            response.close()
        else:
            image = Image.open(image_link)

        return image
    except (URLError, FileNotFoundError, UnidentifiedImageError):
        raise ImageLoadError(f"{image_link} | Failed to open image")


def get_image_bytes(image: Image.Image) -> bytes:
    """Extracts bytes from a given Image file"""
    image_bytes_arr = BytesIO()
    image.save(image_bytes_arr, format=image.format)
    return image_bytes_arr.getvalue()
