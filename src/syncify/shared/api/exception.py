from requests import Response

from syncify.shared.exception import SyncifyError


class APIError(SyncifyError):
    """
    Exception raised for API errors.

    :param message: Explanation of the error.
    :param response: The :py:class:`Response` related to the error.
    """

    def __init__(self, message: str | None = None, response: Response | None = None):
        self.message = message
        self.response = response
        formatted = f"Status code: {response.status_code} | {message}" if response else message
        super().__init__(formatted)


class RequestError(APIError):
    """Exception raised for errors raised when making requests to an API."""