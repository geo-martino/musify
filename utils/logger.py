import logging
import os
import re
import sys
from datetime import datetime as dt
from os.path import join, dirname, exists

class logStdOutFilter(logging.Filter):
    def __init__(self, levels: list = None):
        """
        :param levels: str, default=None. Accepted log levels to return i.e. 'info', 'debug'
            If None, set to current log level.
        """

        self.levels = levels if levels else [self.__level]

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        if record.levelno in self.levels:
            return record


class logFileFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        record.msg = re.sub("\n$", "", record.msg)
        record.msg = re.sub("\33.*?m", "", record.msg)
        record.funcName = f"{record.module}.{record.funcName}"

        return record

class Logger:

    def __init__(self):
        self._log_path = None
        self._log_file = None
        self._logger = None

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """
        Custom exception handler. Handles exceptions through logger.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self._logger.critical(
            "CRITICAL ERROR: Uncaught Exception", exc_info=(
                exc_type, exc_value, exc_traceback))

    def _get_logger(self) -> logging.Logger:
        """
        Return logger object formatted for stdout and file handlers.

        :return logging.Logger. Logger object
        """
        # set log file path
        self._log_path = join(dirname(dirname(__file__)), "_log")
        self._log_file = join(self._log_path, f"{self._output_name}.log")
        if not exists(self._log_path):  # if log folder doesn't exist
            os.makedirs(self._log_path)  # create log folder

        levels = [logging.INFO, logging.WARNING]
        if self._verbose < 2:
            filter = logStdOutFilter(levels=levels)
        elif self._verbose == 2:
            filter = logStdOutFilter(levels=levels + [logging.DEBUG])
        else:
            filter = logFileFilter()

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
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        for h in logger.handlers:
            logger.removeHandler(h)

        # handler for stdout
        stdout_h = logging.StreamHandler(stream=sys.stdout)
        stdout_h.setLevel(logging.INFO if self._verbose < 2 else logging.DEBUG)
        stdout_h.setFormatter(stdout_format)
        stdout_h.addFilter(filter)
        logger.addHandler(stdout_h)

        # handler for file output
        file_h = logging.FileHandler(self._log_file, 'w', encoding='utf-8')
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(file_format)
        file_h.addFilter(logFileFilter())
        logger.addHandler(file_h)

        # return exceptions to logger
        sys.excepthook = self._handle_exception

        self._logger = logger

    def _close_handlers(self):
        handlers = self._logger.handlers[:]
        for handler in handlers:
            self._logger.removeHandler(handler)
            handler.close()