"""
Exceptions relating to file operations.
"""
from musify.exception import MusifyError


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
