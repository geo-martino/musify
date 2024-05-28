"""
Exceptions relating to file operations.
"""
from pathlib import Path

from musify.exception import MusifyError


class FileError(MusifyError):
    """
    Exception raised for file errors.

    :param file: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, file: str | Path | None = None, message: str | None = None):
        self.file = Path(file)
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
        self.message = message
        super().__init__(file=filetype, message=message)


class FileDoesNotExistError(FileError, FileNotFoundError):
    """
    Exception raised when a file cannot be found.

    :param path: The path that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, path: str | Path, message: str = "File cannot be found"):
        self.message = message
        super().__init__(file=path, message=message)


class UnexpectedPathError(FileError):
    """
    Exception raised when a path is invalid.
    Usually raised when a directory is given when a file was expected and vice versa.

    :param path: The path that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, path: str | Path, message: str = "Invalid path given"):
        self.message = message
        super().__init__(file=path, message=message)


class ImageLoadError(FileError):
    """Exception raised for errors in loading an image."""
