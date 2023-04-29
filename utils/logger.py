import logging
import os
import re
import sys
from datetime import datetime
from os.path import join, dirname, exists
from typing import Literal, Optional


class LogStdOutFilter(logging.Filter):
    def __init__(self, levels: list[int] = None):
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

    def __init__(self):
        self._log_filename = ".".join((self.__class__.__module__, self.__class__.__qualname__))
        self._log_path = join(self._log_folder, f"{self._log_filename}.log")

        self._logger = None
        self._set_logger()

    @classmethod
    def set_log_path(cls, folder: Optional[str], run_name: Optional[str], run_dt: datetime = datetime.now()):
        if folder is None:
            folder = join(dirname(dirname(__file__)), "_log")
        if run_name is None:
            run_name = "unknown"

        cls.log_folder = join(folder, run_name, run_dt.strftime("%Y-%m-%d_%H.%M.%S"))

    @classmethod
    def set_verbosity(cls, verbose: int):
        cls._verbose = verbose

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
        if not exists(self._log_folder):  # if log folder doesn't exist
            os.makedirs(self._log_folder)  # create log folder

        levels: list[Literal] = [logging.INFO, logging.WARNING]
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