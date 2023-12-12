from typing import Any

from syncify.exception import SyncifyError
from .enums import RemoteIDType, RemoteItemType


class RemoteError(SyncifyError):
    """Exception raised for remote errors"""


###########################################################################
## Type errors
###########################################################################
class RemoteIDTypeError(RemoteError):
    """
    Exception raised for remote ID type errors.

    :param message: Explanation of the error.
    :param kind: The ID type related to the error.
    """

    def __init__(self, message: str | None = None, kind: RemoteIDType | None = None, value: Any = None):
        self.kind = kind
        self.message = message
        formatted = f"{kind} | {message}" if kind else message
        formatted += f": {value}" if value else ""
        super().__init__(formatted)


class RemoteItemTypeError(RemoteError):
    """
    Exception raised for remote item type errors.

    :param message: Explanation of the error.
    :param kind: The item type related to the error.
    """

    def __init__(self, message: str | None = None, kind: RemoteItemType | None = None, value: Any = None):
        self.kind = kind
        formatted = f"{kind} | {message}" if kind else message
        formatted += f": {value}" if value else ""
        super().__init__(formatted)
