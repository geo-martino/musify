"""
Functionality relating to reading and writing images.
"""
from http.client import HTTPResponse
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request

from musify.file.exception import ImageLoadError
from musify.utils import required_modules_installed

try:
    from PIL import Image, UnidentifiedImageError
    ImageType = Image.Image
except ImportError:
    Image = None
    UnidentifiedImageError = None
    ImageType = None

REQUIRED_MODULES = [Image, UnidentifiedImageError]


def open_image(source: str | bytes | Path | Request) -> ImageType:
    """
    Open Image object from a given URL or file path

    :return: The loaded :py:class:`Image.Image`
    :raise ImageLoadError: If the image cannot be loaded.
    :raise ModuleImportError: If required modules are not installed.
    """
    required_modules_installed(REQUIRED_MODULES, "open_image")

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


def get_image_bytes(image: ImageType) -> bytes:
    """
    Extracts bytes from a given Image file.

    :raise ModuleImportError: If required modules are not installed.
    """
    required_modules_installed(REQUIRED_MODULES, "get_image_bytes")

    image_bytes_arr = BytesIO()
    image.save(image_bytes_arr, format=image.format)
    return image_bytes_arr.getvalue()
