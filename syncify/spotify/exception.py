from typing import Optional, Any

from syncify.spotify import IDType, ItemType


class SpotifyError(Exception):
    """
    Exception raised for Spotify ID errors.

    :param message: Explanation of the error.
    """

    def __init__(self, message: Optional[str] = None):
        self.message = message
        super().__init__(message)


class SpotifyItemError(SpotifyError):
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


class SpotifyCollectionError(SpotifyError):
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


class APIError(SpotifyError):
    """Exception raised for Spotify API errors."""


###########################################################################
## Type errors
###########################################################################
class SpotifyIDTypeError(SpotifyError):
    """
    Exception raised for Spotify ID type errors.

    :param message: Explanation of the error.
    :param kind: The ID type related to the error.
    """

    def __init__(self, message: Optional[str] = None, kind: Optional[IDType] = None, value: Any = None):
        self.kind = kind
        self.message = message
        formatted = f"{kind} | {message}" if kind else message
        formatted += f": {value}" if value else ""
        super().__init__(formatted)


class SpotifyItemTypeError(SpotifyError):
    """
    Exception raised for Spotify item type errors.

    :param message: Explanation of the error.
    :param kind: The item type related to the error.
    """

    def __init__(self, message: Optional[str] = None, kind: Optional[ItemType] = None, value: Any = None):
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        formatted += f": {value}" if value else ""
        super().__init__(formatted)
