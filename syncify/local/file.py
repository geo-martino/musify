from abc import ABCMeta, abstractmethod
from http.client import HTTPResponse
from io import BytesIO
from os.path import splitext, basename, dirname
from typing import List
from urllib.error import URLError
from urllib.request import urlopen

from PIL import Image, UnidentifiedImageError

from syncify.local.exception import IllegalFileTypeError


class File(metaclass=ABCMeta):

    @property
    @abstractmethod
    def path(self) -> str:
        raise NotImplementedError

    @property
    def folder(self) -> str:
        return basename(dirname(self.path))

    @property
    def filename(self) -> str:
        return splitext(basename(self.path))[0]

    @property
    def ext(self) -> str:
        return splitext(self.path)[1].lower()

    @property
    @abstractmethod
    def valid_extensions(self) -> List[str]:
        """Allowed extensions in lowercase"""
        raise NotImplementedError

    def _validate_type(self, path: str) -> None:
        """Raises exception if the path's extension is not accepted"""
        ext = splitext(path)[1].lower()
        if ext not in self.valid_extensions:
            raise IllegalFileTypeError(
                ext,
                f"Not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self.valid_extensions)}"
            )


class ImageLoadError(Exception):
    """Exception raised for errors in loading an image.

    :param message: Explanation of the error.
    """

    def __init__(self, message: str = "Image failed to load"):
        self.message = message
        super().__init__(self.message)


def open_image(image_link: str) -> Image.Image:
    """
    Open Image object from a given URL or file path

    :exception ImageLoadError: If the image cannot be loaded.
    """

    try:  # open image from link
        if image_link.startswith("http"):
            response: HTTPResponse = urlopen(image_link)
            image = Image.open(response.read())
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
