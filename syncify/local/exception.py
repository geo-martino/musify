from typing import Any


class LocalError(Exception):
    """
    Exception raised for local errors.

    :param message: Explanation of the error.
    """
    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(message)


class LocalItemError(LocalError):
    """
    Exception raised for local item errors.

    :param message: Explanation of the error.
    :param kind: The item type related to the error.
    """
    def __init__(self, message: str | None = None, kind: str | None = None):
        self.message = message
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        super().__init__(formatted)


class LocalCollectionError(LocalError):
    """
    Exception raised for local collection errors.

    :param message: Explanation of the error.
    :param kind: The collection type related to the error.
    """
    def __init__(self, message: str | None = None, kind: str | None = None):
        self.message = message
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        super().__init__(formatted)


class LocalProcessorError(LocalError):
    """Exception raised for errors related to track processors."""


###########################################################################
## File errors
###########################################################################
class FileError(LocalError):
    """
    Exception raised for file errors.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: str | None = None, message: str | None = None):
        self.filetype = filetype
        self.message = message
        formatted = f"{filetype} | {message}" if filetype else message
        super().__init__(formatted)


class IllegalFileTypeError(FileError):
    """
    Exception raised for unrecognised file types.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: str, message: str = "File type not recognised"):
        self.filetype = filetype
        self.message = message
        super().__init__(filetype=filetype, message=message)


class ImageLoadError(FileError):
    """Exception raised for errors in loading an image."""


###########################################################################
## MusicBee errors
###########################################################################
class MusicBeeError(LocalError):
    """Exception raised for errors related to MusicBee logic."""


class FieldError(MusicBeeError):
    """
    Exception raised for errors related to MusicBee field.

    :param message: Explanation of the error.
    """
    def __init__(self, message: str | None = None, field: Any | None = None):
        self.field = field
        self.message = message
        formatted = f"{message}: {field}" if field else message
        super().__init__(message=formatted)


class LimitError(MusicBeeError):
    """Exception raised for errors related to MusicBee limit settings."""
