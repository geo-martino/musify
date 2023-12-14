import inspect
import logging
import os
import re
import sys
from collections.abc import Collection, Container
from datetime import datetime
from os.path import join, dirname, exists, splitext, split
from typing import Any

from tqdm.auto import tqdm as tqdm_auto
from tqdm.std import tqdm as tqdm_std

from syncify import PROGRAM_NAME
from syncify.utils.helpers import limit_value

module_width = 40

INFO_EXTRA = logging.INFO - 1
REPORT = logging.INFO - 3
STAT = logging.DEBUG + 3

logging.addLevelName(INFO_EXTRA, "INFO_EXTRA")
logging.addLevelName(REPORT, "REPORT")
logging.addLevelName(STAT, "STAT")


def format_full_func_name(record: logging.LogRecord, width: int = module_width) -> None:
    """
    Set fully qualified path name to function including class name to the given record.
    Optionally, provide a max ``width`` to attempt to truncate the path name to
    by taking only the first letter of each part of the path until the length is equal to ``width``.
    """
    path = record.funcName.split(".")[-1]
    stack = inspect.stack()
    f_locals = stack[8][0].f_locals

    if "self" in f_locals:  # is a valid and initialised object
        path = splitext(inspect.getfile(f_locals["self"].__class__))[0]

        # get relative path to 'syncify' sources root
        folder = ""
        path_split = []
        while folder != PROGRAM_NAME.casefold():
            path, folder = split(path)
            path_split.append(folder)

        # produce fully qualified path
        path_split = list(reversed(path_split[:-1]))
        path_split.extend([f_locals["self"].__class__.__name__, record.funcName.split(".")[-1]])
        path = ".".join(path_split)

    # truncate long paths by taking first letters of each part until short enough
    path_split = path.split(".")
    for i, part in enumerate(path_split):
        if len(path) <= width:
            break

        path_split[i] = part[0]
        path = ".".join(path_split)

    record.funcName = path


class LogStdOutFilter(logging.Filter):
    """Filter for logging to stdout."""

    def __init__(self, levels: Container[int] = ()):
        """
        :param levels: Accepted log levels to return i.e. 'info', 'debug'
            If None, set to current log level.
        """
        super().__init__()
        self.levels: Container[int] = levels

    # noinspection PyMissingOrEmptyDocstring
    def filter(self, record: logging.LogRecord) -> logging.LogRecord | None:
        if record.levelno not in self.levels:
            return
        format_full_func_name(record)
        return record


class LogFileFilter(logging.Filter):
    """Filter for logging to a file."""

    # noinspection PyMissingOrEmptyDocstring
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        # record.msg = re.sub(r"\n$", "", record.msg)
        record.msg = re.sub("\33.*?m", "", record.msg)
        format_full_func_name(record)
        return record


class SyncifyLogger(logging.Logger):
    """The logger for all logging operations in Syncify."""

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

    def __copy__(self):
        """Do not copy logger"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy logger"""
        return self


class Logger:
    """Base logger class. Classes can inherit this class to gain logging functionality."""
    log_folder: str = None
    dt_format: str = "%Y-%m-%d_%H.%M.%S"

    is_dev: bool = False

    verbosity: int = 0
    compact: bool = False
    detailed: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.log_folder is None:
            self.set_dev()

        self.log_filename = ".".join((self.__class__.__module__, self.__class__.__qualname__))
        self.log_path = join(self.log_folder, f"{self.log_filename}.log")

        self.logger: SyncifyLogger | None = None
        self._set_logger()

    @classmethod
    def set_log_folder(
            cls,
            folder: str = join(dirname(dirname(__file__)), "_logs"),
            run_dt: datetime = datetime.now()
    ):
        """Set the path of the log folder. Defaults to a folder in the source code's root"""
        cls.log_folder = join(folder, run_dt.strftime(cls.dt_format))

    @classmethod
    def set_dev(cls) -> None:
        """Set defaults for running in dev mode"""
        cls.set_log_folder("_logs/_dev")
        cls.verbosity = 5
        cls.is_dev = True

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Custom exception handler. Handles exceptions through logger."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.critical(
            "CRITICAL ERROR: Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    def _set_logger(self) -> None:
        """Set logger object formatted for stdout and file handlers."""
        # set log file path
        if not self.is_dev and not exists(self.log_folder):  # if log folder doesn't exist
            os.makedirs(self.log_folder)  # create log folder

        # get logger and clear default handlers
        self.logger = SyncifyLogger(self.log_filename)
        self.logger.setLevel(logging.DEBUG)
        for h in self.logger.handlers:
            self.logger.removeHandler(h)

        # set handlers
        self._set_stdout_handler()
        if not self.is_dev:
            self._set_file_handler()

        # return exceptions to logger
        sys.excepthook = self._handle_exception

    # noinspection SpellCheckingInspection
    def _set_stdout_handler(self) -> None:
        """Sets the stdout handler for the logger"""
        # logging formats
        stdout_pretty = (
            "\33[91m{asctime}.{msecs:0<3.0f}\33[0m | "
            "[\33[92m{levelname:>8}\33[0m] "
            f"\33[1;96m{{funcName:<{module_width}.{module_width}}}\33[0m "
            "[\33[95m{lineno:>4}\33[0m] | "
            "{message}"
        )
        stdout_format = logging.Formatter(
            fmt=stdout_pretty if self.detailed or self.verbosity >= 4 else "{message}",
            datefmt="%Y-%m-%d %H:%M:%S", style="{"
        )

        levels: list[int] = [logging.INFO, logging.ERROR, logging.CRITICAL]
        level_base = logging.DEBUG
        if self.verbosity == 0:
            log_filter = LogStdOutFilter(levels=levels)
            level_base = logging.INFO
        elif self.verbosity == 1:
            log_filter = LogStdOutFilter(levels=levels + [INFO_EXTRA, REPORT])
            level_base = REPORT
        elif self.verbosity == 2:
            log_filter = LogStdOutFilter(levels=levels + [INFO_EXTRA, REPORT, STAT])
            level_base = STAT
        elif self.verbosity == 3:
            log_filter = LogStdOutFilter(levels=levels + [INFO_EXTRA, REPORT, STAT, logging.WARNING, logging.DEBUG])
            level_base = STAT
        else:
            log_filter = LogFileFilter()

        # handler for stdout
        stdout_h = logging.StreamHandler(stream=sys.stdout)
        stdout_h.set_name("stdout")
        stdout_h.setLevel(level_base)
        stdout_h.setFormatter(stdout_format)
        stdout_h.addFilter(log_filter)
        self.logger.addHandler(stdout_h)

    # noinspection SpellCheckingInspection
    def _set_file_handler(self) -> None:
        """Sets the file handler for the logger."""
        file_format = logging.Formatter(
            fmt="{asctime}.{msecs:0<3.0f} | "
                "[{levelname:>8}] "
                f"{{funcName:<{module_width}.{module_width}}} "
                "[{lineno:>4}] | "
                "{message}",
            datefmt="%Y-%m-%d %H:%M:%S", style="{"
        )

        file_h = logging.FileHandler(self.log_path, 'w', encoding="utf-8")
        file_h.set_name("file")
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(file_format)
        file_h.addFilter(LogFileFilter())
        self.logger.addHandler(file_h)

    def _get_handler(self, name: str) -> logging.Handler | None:
        """Get the logging handler that matches the given ``name``"""
        handlers = self.logger.handlers[:]
        for handler in handlers:
            if handler.name == name:
                return handler

    def close_handlers(self) -> None:
        """Close all handlers and end logging"""
        handlers = self.logger.handlers[:]
        for handler in handlers:
            self.logger.removeHandler(handler)
            handler.close()

    @staticmethod
    def get_max_width(items: Collection[Any], min_width: int = 15, max_width: int = 50) -> int:
        """Get max width of given list of items for column-aligned logging"""
        if len(items) == 0:
            return 0
        max_len = len(max(map(str, items), key=len))
        return limit_value(value=max_len + 1, floor=min_width, ceil=max_width)

    @staticmethod
    def align_and_truncate(value: Any, max_width: int = 0, right_align: bool = False) -> str:
        """Align string with space padding. Truncate any string longer than max width with ..."""
        if max_width == 0:
            return value
        truncated = str(value)[:(max_width - 3)] + "..." if not right_align else "..." + str(value)[-(max_width - 3):]
        return f"{value if len(str(value)) < max_width else truncated:<{max_width}}"

    def get_progress_bar(self, **kwargs) -> tqdm_std:
        """Wrapper for tqdm progress bar. For kwargs, see :py:class:`tqdm_std`"""
        # noinspection SpellCheckingInspection
        preset_keys = ("leave", "disable", "file", "ncols", "colour", "smoothing", "position")
        try:
            cols = os.get_terminal_size().columns
        except OSError:
            cols = 120

        return tqdm_auto(
            leave=kwargs.get("leave", self.verbosity >= 3 and self._get_handler("stdout").level != logging.DEBUG),
            disable=kwargs.get("disable", False),
            file=sys.stdout,
            ncols=cols,
            colour=kwargs.get("colour", "green"),
            smoothing=0.1,
            position=None,
            **{k: v for k, v in kwargs.items() if k not in preset_keys}
        )

    def print_line(self, level: int = logging.CRITICAL + 1) -> None:
        """Print a new line only when : DEBUG < ``logger level`` <= ``level``"""
        handler = self._get_handler("stdout")
        if not self.compact and logging.DEBUG < handler.level <= level:
            print()
