from typing import Any


class SyncifyError(Exception):
    """Generic base class for all Syncify-related errors"""


class SyncifyTypeError(SyncifyError):
    """Exception raised for invalid item types."""
    def __init__(self, kind: Any, message: str = "Invalid item type given"):
        self.message = message
        super().__init__(f"{self.message}: {kind}")


class SyncifyEnumError(SyncifyError):
    """Exception raised when searching enums gives an exception.

    :param value: The value that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, value: Any, message: str = "Could not find enum"):
        self.message = message
        super().__init__(f"{self.message}: {value}")
