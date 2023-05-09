import logging
import os
import re
import sys
from datetime import datetime
from os.path import join, dirname, exists
from typing import Literal, Optional, List, Collection, Any, Type, Iterable

from tqdm.asyncio import tqdm_asyncio
from tqdm.auto import tqdm as tqdm_auto
from tqdm.std import tqdm


class LogStdOutFilter(logging.Filter):
    def __init__(self, levels: List[int] = None):
        """
        :param levels: str, default=None. Accepted log levels to return i.e. 'info', 'debug'
            If None, set to current log level.
        """
        super().__init__()
        self.levels = levels

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        if record.levelno in self.levels:
            return record


class LogFileFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        record.msg = re.sub("\n$", "", record.msg)
        record.msg = re.sub("\33.*?m", "", record.msg)
        record.funcName = f"{record.module}.{record.funcName}"

        return record


class Logger:

    _log_folder: str = None
    _verbose: int = 0
    _is_dev: bool = False

    def __init__(self):
        if self._log_folder is None:
            self.set_dev()

        self._log_filename = ".".join((self.__class__.__module__, self.__class__.__qualname__))
        self._log_path = join(self._log_folder, f"{self._log_filename}.log")

        self._logger = None
        self._set_logger()

    @classmethod
    def set_log_folder(
            cls, folder: Optional[str], run_name: str = "unknown", run_dt: datetime = datetime.now()
    ) -> None:
        if folder is None:
            folder = join(dirname(dirname(__file__)), "_log")

        cls._log_folder = join(folder, run_name, run_dt.strftime("%Y-%m-%d_%H.%M.%S"))

    @classmethod
    def set_verbosity(cls, verbose: int) -> None:
        cls._verbose = verbose

    @classmethod
    def set_dev(cls) -> None:
        cls.set_log_folder("___log_dev", "dev")
        cls.set_verbosity(5)
        cls._is_dev = True

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Custom exception handler. Handles exceptions through logger."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self._logger.critical(
            "CRITICAL ERROR: Uncaught Exception", exc_info=(
                exc_type, exc_value, exc_traceback))

    def _set_logger(self) -> None:
        """Set logger object formatted for stdout and file handlers."""
        # set log file path
        if not self._is_dev and not exists(self._log_folder):  # if log folder doesn't exist
            os.makedirs(self._log_folder)  # create log folder

        levels: List[Literal] = [logging.INFO, logging.WARNING]
        if self._verbose < 2:
            log_filter = LogStdOutFilter(levels=levels)
        elif self._verbose == 2:
            log_filter = LogStdOutFilter(levels=levels + [logging.DEBUG])
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
        if self._verbose > 3:
            stdout_format = file_format
        
        # get logger and clear default handlers
        self._logger = logging.getLogger(self._log_filename)
        self._logger.setLevel(logging.DEBUG)
        for h in self._logger.handlers:
            self._logger.removeHandler(h)

        # handler for stdout
        stdout_h = logging.StreamHandler(stream=sys.stdout)
        stdout_h.setLevel(logging.INFO if self._verbose < 2 else logging.DEBUG)
        stdout_h.setFormatter(stdout_format)
        stdout_h.addFilter(log_filter)
        self._logger.addHandler(stdout_h)

        # handler for file output
        if not self._is_dev:
            file_h = logging.FileHandler(self._log_path, 'w', encoding='utf-8')
            file_h.setLevel(logging.DEBUG)
            file_h.setFormatter(file_format)
            file_h.addFilter(LogFileFilter())
            self._logger.addHandler(file_h)

        # return exceptions to logger
        sys.excepthook = self._handle_exception

    def _close_handlers(self):
        handlers = self._logger.handlers[:]
        for handler in handlers:
            self._logger.removeHandler(handler)
            handler.close()

    @staticmethod
    def _get_max_width(items: Collection[Any], max_width: int = 50) -> int:
        if len(items) == 0:
            return 0
        items = [str(item) for item in items]
        return min(len(max(items, key=len)) + 1, max_width)

    @staticmethod
    def _truncate_align_str(value: Any, max_width: int = 0) -> str:
        if max_width == 0:
            return value
        return f"{value if len(str(value)) < 50 else str(value)[:47] + '...':<{max_width}}"

    @staticmethod
    def _get_progress_bar(**kwargs) -> tqdm_asyncio:
        """Wrapper for tqdm progress bar. For kwargs, see :class:`tqdm`"""
        return tqdm_auto(
            leave=True,  # self._verbose > 0,
            disable=False,  # self._verbose > 2 and self._verbose < 2,
            file=sys.stdout,
            **kwargs
        )
