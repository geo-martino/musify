import logging
import os
import re
import sys
from datetime import datetime
from os.path import join, dirname, exists
from typing import Literal, List, Collection, Any, Union

from tqdm.asyncio import tqdm_asyncio
from tqdm.auto import tqdm as tqdm_auto


class LogStdOutFilter(logging.Filter):
    def __init__(self, levels: List[int] = None):
        """
        :param levels: str, default=None. Accepted log levels to return i.e. 'info', 'debug'
            If None, set to current log level.
        """
        super().__init__()
        self.levels = levels

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        if self.levels is None or record.levelno in self.levels:
            return record


class LogFileFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        # record.msg = re.sub("\n$", "", record.msg)
        record.msg = re.sub("\33.*?m", "", record.msg)
        record.funcName = f"{record.module}.{record.funcName}"

        return record


class Logger:
    log_folder: str = None
    verbosity: int = 0
    is_dev: bool = False
    dt_format: str = "%Y-%m-%d_%H.%M.%S"

    def __init__(self):
        if self.log_folder is None:
            self.set_dev()

        self.log_filename = ".".join((self.__class__.__module__, self.__class__.__qualname__))
        self.log_path = join(self.log_folder, f"{self.log_filename}.log")

        self.logger = None
        self._set_logger()

    @classmethod
    def set_log_folder(cls,
                       folder: str = join(dirname(dirname(__file__)), "_logs"),
                       run_dt: datetime = datetime.now()) -> None:
        cls.log_folder = join(folder, run_dt.strftime(cls.dt_format))

    @classmethod
    def set_verbosity(cls, verbosity: int = 0) -> None:
        cls.verbosity = verbosity

    @classmethod
    def set_dev(cls) -> None:
        cls.set_log_folder("_logs/_dev")
        cls.set_verbosity(5)
        cls.is_dev = True

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Custom exception handler. Handles exceptions through logger."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.critical("CRITICAL ERROR: Uncaught Exception",
                             exc_info=(exc_type, exc_value, exc_traceback))

    def _set_logger(self) -> None:
        """Set logger object formatted for stdout and file handlers."""
        # set log file path
        if not self.is_dev and not exists(self.log_folder):  # if log folder doesn't exist
            os.makedirs(self.log_folder)  # create log folder

        levels: List[Literal] = [logging.INFO, logging.ERROR, logging.CRITICAL]
        if self.verbosity == 0:
            log_filter = LogStdOutFilter(levels=levels)
        elif self.verbosity == 1:
            log_filter = LogStdOutFilter(levels=levels + [logging.WARNING])
        elif self.verbosity == 2:
            log_filter = LogStdOutFilter(levels=levels + [logging.WARNING, logging.DEBUG])
        else:
            log_filter = LogFileFilter()

        # logging formats
        stdout_format = logging.Formatter(
            fmt="%(message)s",
            datefmt="%y-%b-%d %H:%M:%S"
        )
        file_format = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)8s] [%(funcName)-40s:%(lineno)4d] --- %(message)s",
            datefmt="%y-%b-%d %H:%M:%S"
        )
        if self.verbosity > 3:
            stdout_format = file_format

        # get logger and clear default handlers
        self.logger = logging.getLogger(self.log_filename)
        self.logger.setLevel(logging.DEBUG)
        for h in self.logger.handlers:
            self.logger.removeHandler(h)

        # handler for stdout
        stdout_h = logging.StreamHandler(stream=sys.stdout)
        stdout_h.set_name("stdout")
        stdout_h.setLevel(logging.INFO if self.verbosity < 2 else logging.DEBUG)
        stdout_h.setFormatter(stdout_format)
        stdout_h.addFilter(log_filter)
        self.logger.addHandler(stdout_h)

        # handler for file output
        if not self.is_dev:
            file_h = logging.FileHandler(self.log_path, 'w', encoding='utf-8')
            file_h.set_name("file")
            file_h.setLevel(logging.DEBUG)
            file_h.setFormatter(file_format)
            file_h.addFilter(LogFileFilter())
            self.logger.addHandler(file_h)

        # return exceptions to logger
        sys.excepthook = self._handle_exception

    def _close_handlers(self):
        handlers = self.logger.handlers[:]
        for handler in handlers:
            self.logger.removeHandler(handler)
            handler.close()

    @staticmethod
    def limit_value(
            value: Union[int, float], floor: Union[int, float] = 1, ceil: Union[int, float] = 50
    ) -> Union[int, float]:
        """Limits a given ``value`` to always be between some ``floor`` and ``ceil``"""
        return max(min(value, ceil), floor)

    @staticmethod
    def get_max_width(items: Collection[Any], max_width: int = 50) -> int:
        if len(items) == 0:
            return 0
        items = [str(item) for item in items]
        return min(len(max(items, key=len)) + 1, max_width)

    @staticmethod
    def truncate_align_str(value: Any, max_width: int = 0) -> str:
        if max_width == 0:
            return value
        return f"{value if len(str(value)) < 50 else str(value)[:47] + '...':<{max_width}}"

    def get_progress_bar(self, **kwargs) -> tqdm_asyncio:
        """Wrapper for tqdm progress bar. For kwargs, see :class:`tqdm`"""
        preset_keys = ["leave", "disable", "colour", "position"]
        stdout_h = [handler for handler in self.logger.handlers if handler.name == "stdout"][0]
        return tqdm_auto(
            leave=kwargs.get("leave", self.verbosity > 0) and kwargs.get("position", 0) == 0,
            disable=kwargs.get("disable", self.verbosity == 0 and stdout_h.level == logging.DEBUG),
            file=sys.stdout,
            ncols=120,
            colour=kwargs.get("colour", "green"),
            smoothing=0.5,
            position=kwargs.get("position", 0),
            **{k: v for k, v in kwargs.items() if k not in preset_keys}
        )

    def print_line(self):
        if self.logger.handlers[0].level != logging.DEBUG:
            print()
