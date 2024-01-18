"""
Exceptions relating to local operations.
"""

from musify.shared.exception import MusifyError


class LocalError(MusifyError):
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


###########################################################################
## Library errors
###########################################################################
class LocalLibraryError(LocalError):
    """Exception raised for errors related to :py:class:`LocalLibrary` logic."""


class MusicBeeError(LocalLibraryError):
    """Exception raised for errors related to :py:class:`MusicBee` logic."""


class MusicBeeIDError(MusicBeeError):
    """Exception raised for errors related to MusicBee IDs."""


class XMLReaderError(MusicBeeError):
    """Exception raised for errors related to reading a MusicBee library XML file."""
