"""
All logging filters specific to this package.
"""
import inspect
import logging.handlers
import re
from pathlib import Path

from musify import PROGRAM_NAME


def format_full_func_name(record: logging.LogRecord, width: int = 40) -> None:
    """
    Set fully qualified path name to function including class name to the given record.
    Optionally, provide a max ``width`` to attempt to truncate the path name to
    by taking only the first letter of each part of the path until the length is equal to ``width``.
    """
    last_call = inspect.stack()[8]

    if record.pathname == __file__:
        # custom logging method has been called, reformat call info to actual call method
        record.pathname = last_call.filename
        record.lineno = last_call.lineno
        record.funcName = last_call.function
        record.filename = Path(record.pathname).name
        record.module = record.name.split(".")[-1]

    f_locals = last_call.frame.f_locals
    if "self" not in f_locals:
        path_split = record.name.split(".")
        if record.funcName != "<module>":
            path_split.append(record.funcName)
    else:
        # is a valid and initialised object, extract the class name and determine path to call function from stack
        cls = f_locals["self"].__class__
        path = Path(inspect.getfile(cls)).with_suffix("").joinpath(Path(cls.__name__, record.funcName.split(".")[-1]))

        folder = ""
        path_split = []
        while not folder.casefold().startswith(PROGRAM_NAME.casefold()):  # get relative path to sources root
            folder = path.name
            path = path.parent
            path_split.append(folder)
        path_split.append(PROGRAM_NAME.lower())

        # produce fully qualified path
        path_split = path_split[:-1][::-1]

    # truncate long paths by taking first letters of each part until short enough
    path = ".".join(path_split)
    for i, part in enumerate(path_split):
        if len(path) <= width:
            break
        if not part:
            continue

        # take all upper case characters if they exist in part, else, if all lower case, take first letter
        path_split[i] = re.sub("[a-z_]+", "", part) if re.match("[A-Z]", part) else part[0]
        path = ".".join(path_split)

    record.funcName = path


class LogConsoleFilter(logging.Filter):
    """
    Filter for logging to the console.

    :param module_width: The maximum width a module string can be in the log record.
        Truncates module string if longer that this length.
    """

    __slots__ = ("module_width",)

    def __init__(self, name: str = "", module_width: int = 40):
        super().__init__(name)
        self.module_width = module_width

    # noinspection PyMissingOrEmptyDocstring
    def filter(self, record: logging.LogRecord) -> logging.LogRecord | None:
        format_full_func_name(record, width=self.module_width)
        return record


class LogFileFilter(logging.Filter):
    """
    Filter for logging to a file.

    :param module_width: The maximum width a module string can be in the log record.
        Truncates module string if longer that this length.
    """

    __slots__ = ("module_width",)

    def __init__(self, name: str = "", module_width: int = 40):
        super().__init__(name)
        self.module_width = module_width

    # noinspection PyMissingOrEmptyDocstring
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        record.msg = re.sub("\33.*?m", "", record.msg)
        format_full_func_name(record, width=self.module_width)
        return record
