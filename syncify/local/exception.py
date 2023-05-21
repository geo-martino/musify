from typing import Optional, Any


class LocalError(Exception):
    """
    Exception raised for local errors.

    :param message: Explanation of the error.
    """
    def __init__(self, message: Optional[str] = None):
        self.message = message
        super().__init__(message)


class LocalItemError(LocalError):
    """
    Exception raised for local item errors.

    :param message: Explanation of the error.
    :param kind: The item type related to the error.
    """
    def __init__(self, message: Optional[str] = None, kind: Optional[str] = None):
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
    def __init__(self, message: Optional[str] = None, kind: Optional[str] = None):
        self.message = message
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        super().__init__(formatted)


class FileError(LocalError):
    """
    Exception raised for file errors.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: Optional[str] = None, message: Optional[str] = None):
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
    """
    Exception raised for errors in loading an image.

    :param message: Explanation of the error.
    """

    def __init__(self, filetype: Optional[str] = None, message: str = "Image failed to load"):
        super().__init__(filetype=filetype, message=message)


class MusicBeeError(LocalError):
    """
    Exception raised for errors related to MusicBee logic.

    :param message: Explanation of the error.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message=message)


class FieldError(MusicBeeError):
    """
    Exception raised for errors related to MusicBee field.

    :param message: Explanation of the error.
    """
    def __init__(self, message: Optional[str] = None, field: Optional[Any] = None):
        self.field = field
        self.message = message
        formatted = f"{message}: {field}" if field else message
        super().__init__(message=message)


class LimitError(MusicBeeError):
    """
    Exception raised for errors related to MusicBee limit settings.

    :param message: Explanation of the error.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message=message)


class LocalProcessorError(LocalError):
    """
    Exception raised for errors related to track processors.

    :param message: Explanation of the error.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message=message)
