from typing import Any, Iterable


class SafeDict(dict):
    """Extends dict to ignore missing keys when using format_map operations"""
    def __missing__(self, key):
        return "{" + key + "}"


class SyncifyError(Exception):
    """Generic base class for all Syncify-related errors"""


class SyncifyKeyError(SyncifyError, KeyError):
    """Exception raised for invalid keys."""


class SyncifyValueError(SyncifyError, ValueError):
    """Exception raised for invalid values."""


class SyncifyTypeError(SyncifyError, TypeError):
    """Exception raised for invalid item types."""
    def __init__(self, kind: Any, message: str = "Invalid item type given"):
        self.message = message
        super().__init__(f"{self.message}: {kind}")


class SyncifyAttributeError(SyncifyError, AttributeError):
    """Exception raised for invalid attributes."""


class SyncifyEnumError(SyncifyError):
    """Exception raised when searching enums gives an exception.

    :param value: The value that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, value: Any, message: str = "Could not find enum"):
        self.message = message
        super().__init__(f"{self.message}: {value}")


class ConfigError(SyncifyError):
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
