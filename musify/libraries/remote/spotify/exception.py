"""
Exceptions relating to Spotify operations.
"""
from musify.libraries.remote.core.exception import RemoteError


class SpotifyError(RemoteError):
    """
    Exception raised for Spotify ID errors.

    :param message: Explanation of the error.
    """
    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(message)


class SpotifyItemError(SpotifyError):
    """
    Exception raised for Spotify item errors.

    :param message: Explanation of the error.
    :param kind: The item type related to the error.
    """
    def __init__(self, message: str | None = None, kind: str | None = None):
        self.message = message
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        super().__init__(formatted)


class SpotifyCollectionError(SpotifyError):
    """
    Exception raised for Spotify collection errors.

    :param message: Explanation of the error.
    :param kind: The collection type related to the error.
    """
    def __init__(self, message: str | None = None, kind: str | None = None):
        self.message = message
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        super().__init__(formatted)
