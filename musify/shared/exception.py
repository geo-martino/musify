from collections.abc import Iterable
from typing import Any


class SafeDict(dict):
    """Extends dict to ignore missing keys when using format_map operations"""
    def __missing__(self, key):
        return "{" + key + "}"


class MusifyError(Exception):
    """Generic base class for all Musify-related errors"""


class MusifyKeyError(MusifyError, KeyError):
    """Exception raised for invalid keys."""


class MusifyValueError(MusifyError, ValueError):
    """Exception raised for invalid values."""


class MusifyTypeError(MusifyError, TypeError):
    """Exception raised for invalid item types."""
    def __init__(self, kind: Any, message: str = "Invalid item type given"):
        self.message = message
        super().__init__(f"{self.message}: {kind}")


class MusifyAttributeError(MusifyError, AttributeError):
    """Exception raised for invalid attributes."""


###########################################################################
## Enum errors
###########################################################################
class MusifyEnumError(MusifyError):
    """Exception raised when searching enums gives an exception.

    :param value: The value that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, value: Any, message: str = "Could not find enum"):
        self.message = message
        super().__init__(f"{self.message}: {value}")


class FieldError(MusifyEnumError):
    """
    Exception raised for errors related to field enums.

    :param message: Explanation of the error.
    """
    def __init__(self, message: str | None = None, field: Any | None = None):
        super().__init__(value=field, message=message)


class ConfigError(MusifyError):
    """Exception raised when processing config gives an exception.

    :param key: The key that caused the error.
    :param value: The value that caused the error.
    :param message: Explanation of the error.
    """
    def __init__(self, message: str = "Could not process config", key: Any | None = None, value: Any | None = None):
        suffix = []

        key = "->".join(key) if isinstance(key, Iterable) and not isinstance(key, str) else key
        if key and "{key}" in message:
            message = message.format_map(SafeDict(key=key))
        elif key:
            suffix.append(f"key='{key}'")

        value = ", ".join(value) if isinstance(value, Iterable) and not isinstance(value, str) else value
        if value and "{value}" in message:
            message = message.format_map(SafeDict(value=value))
        elif value:
            suffix.append(f"value='{value}'")

        self.key = key
        self.value = value
        self.message = message
        super().__init__(": ".join([message, " | ".join(suffix)]))
