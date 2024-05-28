"""
Functionality relating to reading and writing images.
"""
from http.client import HTTPResponse
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request

from PIL import Image, UnidentifiedImageError
from yarl import URL

from musify.file.exception import ImageLoadError


def open_image(source: str | bytes | Path | URL | Request) -> Image.Image:
    """
    Open Image object from a given URL or file path

    :return: The loaded :py:class:`Image.Image`
    :raise ImageLoadError: If the image cannot be loaded.
    :raise ModuleImportError: If required modules are not installed.
    """

    try:  # open image from link
        if isinstance(source, URL):
            source = str(source)

        if isinstance(source, Request) or (isinstance(source, str) and source.startswith("http")):
            response: HTTPResponse = urlopen(source)
            image = Image.open(response)
            response.close()
            return image

        elif not isinstance(source, Request):
            return Image.open(source)

    except (URLError, FileNotFoundError, UnidentifiedImageError):
        pass
    raise ImageLoadError(source, "Failed to open image")


def get_image_bytes(image: Image.Image) -> bytes:
    """
    Extracts bytes from a given Image file.

    :raise ModuleImportError: If required modules are not installed.
    """
    image_bytes_arr = BytesIO()
    image.save(image_bytes_arr, format=image.format)
    return image_bytes_arr.getvalue()
