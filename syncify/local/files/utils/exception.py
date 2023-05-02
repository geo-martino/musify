from typing import Any


class IllegalFileTypeError(Exception):
    """Exception raised for unrecognised file types.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: str, message: str = "File type not recognised"):
        self.filetype = filetype
        self.message = message
        super().__init__(f"{filetype} | {self.message}")


class ImageLoadError(Exception):
    """Exception raised for errors in loading an image.

    :param message: Explanation of the error.
    """

    def __init__(self, message: str = "Image failed to load"):
        self.message = message
        super().__init__(self.message)


class EnumNotFoundError(Exception):
    """Exception raised when unable to find an enum by search.

    :param value: The value that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, value: Any, message: str = "Could not find enum"):
        self.message = message
        super().__init__(f"{self.message}: {value}")
