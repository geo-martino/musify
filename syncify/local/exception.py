class IllegalFileTypeError(Exception):
    """Exception raised for unrecognised file types.

    :param filetype: The file type that caused the error.
    :param message: Explanation of the error.
    """

    def __init__(self, filetype: str, message: str = "File type not recognised"):
        self.filetype = filetype
        self.message = message
        super().__init__(f"{filetype} | {self.message}")
