"""
Core exceptions for the entire package.
"""

from typing import Any


class MusifyError(Exception):
    """Generic base class for all Musify-related errors"""


class MusifyKeyError(MusifyError, KeyError):
    """Exception raised for invalid keys."""


class MusifyValueError(MusifyError, ValueError):
    """Exception raised for invalid values."""


class MusifyTypeError(MusifyError, TypeError):
    """Exception raised for invalid types."""
    def __init__(self, kind: Any, message: str = "Invalid item type given"):
        self.message = message
        super().__init__(f"{self.message}: {kind}")


class MusifyAttributeError(MusifyError, AttributeError):
    """Exception raised for invalid attributes."""


###########################################################################
## Enum errors
###########################################################################
class MusifyEnumError(MusifyError):
    """
    Exception raised for errors related to :py:class:`MusifyEnum` implementations.

    :param value: The value that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, value: Any, message: str = "Could not find enum"):
        self.message = message
        super().__init__(f"{self.message}: {value}")


class FieldError(MusifyEnumError):
    """
    Exception raised for errors related to :py:class:`Field` enums.

    :param message: Explanation of the error.
    """
    def __init__(self, message: str | None = None, field: Any | None = None):
        super().__init__(value=field, message=message)


###########################################################################
## File errors
###########################################################################
class FileError(MusifyError):
    """
    Exception raised for file errors.

    :param file: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, file: str | None = None, message: str | None = None):
        self.file = file
        self.message = message
        formatted = f"{file} | {message}" if file else message
        super().__init__(formatted)


class InvalidFileType(FileError):
    """
    Exception raised for unrecognised file types.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: str, message: str = "File type not recognised"):
        self.filetype = filetype
        self.message = message
        super().__init__(file=filetype, message=message)


class FileDoesNotExistError(FileError, FileNotFoundError):
    """
    Exception raised when a file cannot be found.

    :param path: The path that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, path: str, message: str = "File cannot be found"):
        self.path = path
        self.message = message
        super().__init__(file=path, message=message)


class ImageLoadError(FileError):
    """Exception raised for errors in loading an image."""
