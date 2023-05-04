from abc import ABCMeta, abstractmethod
from os.path import splitext
from typing import List


class IllegalFileTypeError(Exception):
    """Exception raised for unrecognised file types.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: str, message: str = "File type not recognised"):
        self.filetype = filetype
        self.message = message
        super().__init__(f"{filetype} | {self.message}")


class File(metaclass=ABCMeta):

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