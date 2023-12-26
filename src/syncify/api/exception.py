from syncify.exception import SyncifyError


class APIError(SyncifyError):
    """Exception raised for API errors."""


class RequestError(APIError):
    """Exception raised for errors raised when making requests to an API."""
