import inspect
import logging
import logging.config
import logging.handlers
import os
import re
import shutil
import sys
from collections.abc import Iterable
from datetime import datetime
from glob import glob
from os.path import join, dirname, splitext, split, basename, isfile, sep, isdir, isabs
from typing import Any

from tqdm.auto import tqdm

from musify import PROGRAM_NAME, PACKAGE_ROOT
from musify.processors.time import TimeMapper

LOGGING_DT_FORMAT = "%Y-%m-%d_%H.%M.%S"

###########################################################################
## Setup default Logger with extended levels
###########################################################################
INFO_EXTRA = logging.INFO - 1
logging.addLevelName(INFO_EXTRA, "INFO_EXTRA")
logging.INFO_EXTRA = INFO_EXTRA

REPORT = logging.INFO - 3
logging.addLevelName(REPORT, "REPORT")
logging.REPORT = REPORT

STAT = logging.DEBUG + 3
logging.addLevelName(STAT, "STAT")
logging.STAT = STAT


class MusifyLogger(logging.Logger):
    """The logger for all logging operations in Musify."""

    compact: bool = False
    disable_bars: bool = False
    _bars: list[tqdm] = []

    @property
    def file_paths(self) -> list[str]:
        """Get a list of the paths of all file handlers for this logger"""
        paths = []
        for handler in self.handlers:
            if isinstance(handler, logging.FileHandler):
                paths.append(handler.baseFilename)
        return paths

    @property
    def stdout_handlers(self) -> list[logging.StreamHandler]:
        """Get a list of all :py:class:`logging.StreamHandler` handlers that log to stdout"""
        console_handlers = []
        for handler in self.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                console_handlers.append(handler)
        return console_handlers

    def __init__(self, name: str, level: int | str = logging.NOTSET):
        super().__init__(name=name, level=level)

    def info_extra(self, msg, *args, **kwargs) -> None:
        """Log 'msg % args' with severity 'INFO_EXTRA'."""
        if self.isEnabledFor(INFO_EXTRA):
            self._log(INFO_EXTRA, msg, args, **kwargs)

    def report(self, msg, *args, **kwargs) -> None:
        """Log 'msg % args' with severity 'REPORT'."""
        if self.isEnabledFor(REPORT):
            self._log(REPORT, msg, args, **kwargs)

    def stat(self, msg, *args, **kwargs) -> None:
        """Log 'msg % args' with severity 'STAT'."""
        if self.isEnabledFor(STAT):
            self._log(STAT, msg, args, **kwargs)

    def print(self, level: int = logging.CRITICAL + 1) -> None:
        """Print a new line only when DEBUG < ``logger level`` <= ``level`` for all console handlers"""
        if not self.compact and all(logging.DEBUG < h.level <= level for h in self.stdout_handlers):
            print()

    def get_progress_bar[T: Any](
            self,
            iterable: Iterable[T] | None = None,
            total: T | int | None = None,
            **kwargs
    ) -> tqdm | Iterable[T]:
        """Wrapper for tqdm progress bar. For kwargs, see :py:class:`tqdm_std`"""
        # noinspection SpellCheckingInspection
        preset_keys = ("leave", "disable", "file", "ncols", "colour", "smoothing", "position")

        try:
            cols = os.get_terminal_size().columns
        except OSError:
            cols = 120

        # clear closed bars
        self._bars = [bar for bar in self._bars if bar.n < bar.total]

        # determine the level of bar to generate and whether to leave the bar based on current active count
        position = kwargs.get("position", abs(min(bar.pos for bar in self._bars)) + 1 if self._bars else 0)
        leave_default = all(h.level > logging.DEBUG for h in self.stdout_handlers) and position == 0
        leave = kwargs["leave"] if kwargs.get("leave") is not None else leave_default

        bar = tqdm(
            iterable=iterable,
            total=total,
            leave=leave,
            disable=self.disable_bars or kwargs.get("disable", False),
            file=sys.stdout,
            ncols=cols,
            colour=kwargs.get("colour", "blue"),
            smoothing=0.1,
            position=position,
            **{k: v for k, v in kwargs.items() if k not in preset_keys}
        )
        self._bars.append(bar)
        return bar

    def __copy__(self):
        """Do not copy logger"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy logger"""
        return self


logging.setLoggerClass(MusifyLogger)


###########################################################################
## Logging formatters/filters
###########################################################################
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
        record.filename = basename(record.pathname)
        record.module = record.name.split(".")[-1]

    f_locals = last_call.frame.f_locals
    if "self" not in f_locals:
        path_split = record.name.split(".")
        if record.funcName != "<module>":
            path_split.append(record.funcName)
    else:
        # is a valid and initialised object, extract the class name and determine path to call function from stack
        cls = f_locals["self"].__class__
        path = join(splitext(inspect.getfile(cls))[0], cls.__name__, record.funcName.split(".")[-1])

        folder = ""
        path_split = []
        while not folder.casefold().startswith(PROGRAM_NAME.casefold()) and path:  # get relative path to sources root
            path, folder = split(path)
            path_split.append(folder)
        path_split.append(PROGRAM_NAME.lower())

        # produce fully qualified path
        path_split = list(reversed(path_split[:-1]))

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
    """Filter for logging to the console."""

    def __init__(self, name: str = "", module_width: int = 40):
        super().__init__(name)
        self.module_width = module_width

    # noinspection PyMissingOrEmptyDocstring
    def filter(self, record: logging.LogRecord) -> logging.LogRecord | None:
        format_full_func_name(record, width=self.module_width)
        return record


class LogFileFilter(logging.Filter):
    """Filter for logging to a file."""

    def __init__(self, name: str = "", module_width: int = 40):
        super().__init__(name)
        self.module_width = module_width

    # noinspection PyMissingOrEmptyDocstring
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        record.msg = re.sub("\33.*?m", "", record.msg)
        format_full_func_name(record, width=self.module_width)
        return record


###########################################################################
## Logging handlers
###########################################################################
class CurrentTimeRotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """

    :param filename: The full path to the log file.
        Optionally, include a '{}' part in the path to format in the current datetime.
        When None, defaults to '{}.log'
    :param encoding: When not None, it is used to open the file with that encoding.
    :param when: The timespan for 'interval' which is used together to calculate the timedelta.
        Accepts same values as :py:class:`TimeMapper`.
    :param interval: The multiplier for ``when``.
        When combined with ``when``, gives the negative timedelta relative to now
        which is the maximum datetime to keep logs for.
    :param count: The maximum number of files to keep.
    :param delay: When True, the file opening is deferred until the first call to emit().
    :param errors: Used to determine how encoding errors are handled.
    """
    def __init__(
            self,
            filename: str | None = None,
            encoding: str | None = None,
            when: str | None = None,
            interval: int | None = None,
            count: int | None = None,
            delay: bool = False,
            errors: str | None = None
    ):
        self.dt = datetime.now()

        dt_str = self.dt.strftime(LOGGING_DT_FORMAT)
        if not filename:
            filename = "{}.log"
        filename = filename.replace("\\", sep) if sep == "/" else filename.replace("/", sep)
        self.filename = filename.format(dt_str) if "{}" in filename else filename
        if not isabs(self.filename):
            self.filename = join(PACKAGE_ROOT, self.filename)

        self.delta = TimeMapper(when.lower())(interval) if when and interval else None
        self.count = count

        self.removed: list[datetime] = []  # datetime on the files that were removed
        self.rotator(unformatted=filename, formatted=self.filename)

        super().__init__(filename=self.filename, mode="w", encoding=encoding, delay=delay, errors=errors)

    # noinspection PyPep8Naming
    @staticmethod
    def shouldRollover(*_, **__) -> bool:
        """Always returns False. Rotation happens on __init__ and only needs to happen once."""
        return False

    def rotator(self, unformatted: str, formatted: str):
        """
        Rotates the files in the folder on the given ``unformatted`` path.
        Removes files older than ``self.delta`` and the oldest files when number of files >= count
        until number of files <= count. ``formatted`` path is excluded from processing.
        """
        folder = dirname(formatted)
        if not folder:
            return

        # get current files present and prefix+suffix to remove when processing
        paths = tuple(f for f in glob(join(folder, "*")) if f != formatted)
        prefix = unformatted.split("{")[0] if "{" in unformatted and "}" in unformatted else ""
        suffix = unformatted.split("}")[1] if "{" in unformatted and "}" in unformatted else ""

        remaining = len(paths)
        for path in sorted(paths):
            too_many = self.count is not None and remaining >= self.count

            dt_part = path.removeprefix(prefix).removesuffix(suffix)
            try:
                dt_file = datetime.strptime(dt_part, LOGGING_DT_FORMAT)
                too_old = self.delta is not None and dt_file < self.dt - self.delta
            except ValueError:
                dt_file = None
                too_old = False

            is_empty = isdir(path) and not glob(join(path, "*"))

            if too_many or too_old or is_empty:
                os.remove(path) if isfile(path) else shutil.rmtree(path)
                remaining -= 1

                if dt_file and dt_file not in self.removed:
                    self.removed.append(dt_file)
