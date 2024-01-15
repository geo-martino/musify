import logging
import os
import string
import sys
from copy import copy, deepcopy
from datetime import datetime, timedelta
from glob import glob
from os.path import join, basename, splitext
from random import choice

import pytest

from musify import PACKAGE_ROOT
from musify.shared.logger import MusifyLogger, INFO_EXTRA, REPORT, STAT, LOGGING_DT_FORMAT
from musify.shared.logger import format_full_func_name, LogFileFilter, CurrentTimeRotatingFileHandler
from tests.utils import random_str


###########################################################################
## MusifyLogger tests
###########################################################################
@pytest.fixture
def logger() -> MusifyLogger:
    """Yields a :py:class:`MusifyLogger` with all handlers removed for testing"""
    logger = MusifyLogger(__name__)
    logger.compact = False

    for handler in logger.handlers:
        logger.removeHandler(handler)

    return logger


def test_print(logger: MusifyLogger, capfd: pytest.CaptureFixture):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)

    logger.print(logging.ERROR)  # ERROR is above handler level, print line
    assert capfd.readouterr().out == '\n'

    logger.print(logging.WARNING)  # WARNING is below handler level, print line
    assert capfd.readouterr().out == '\n'

    logger.print(logging.INFO)  # INFO is below handler level, don't print line
    assert capfd.readouterr().out == ''

    # compact is True, never print lines
    logger.compact = True

    logger.print(logging.ERROR)
    assert capfd.readouterr().out == ''
    logger.print(logging.WARNING)
    assert capfd.readouterr().out == ''
    logger.print(logging.INFO)
    assert capfd.readouterr().out == ''

    # compact False and handler is at DEBUG level, never print lines
    logger.compact = False
    handler.setLevel(logging.DEBUG)

    logger.print(logging.INFO)
    assert capfd.readouterr().out == ''
    logger.print(logging.DEBUG)
    assert capfd.readouterr().out == ''
    logger.print(0)
    assert capfd.readouterr().out == ''


def test_file_paths(logger: MusifyLogger):
    logger.addHandler(logging.FileHandler(filename="test1.log", delay=True))
    logger.addHandler(logging.FileHandler(filename="test2.log", delay=True))
    assert [basename(path) for path in logger.file_paths] == ["test1.log", "test2.log"]


def test_get_progress_bar(logger: MusifyLogger):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)  # forces leave to be False
    logger.addHandler(handler)
    logger._bars.clear()

    bar = logger.get_progress_bar(iterable=range(0, 50), initial=10, disable=True, file=sys.stderr)

    assert bar.iterable == range(0, 50)
    assert bar.n == 10
    assert bar.total == 50
    assert not bar.leave
    assert bar.disable
    assert bar in logger._bars

    handler.setLevel(logging.WARNING)
    logger.disable_bars = False
    bar = logger.get_progress_bar(
        iterable=range(0, 50),
        initial=10,
        disable=False,
        file=sys.stderr,
        ncols=500,
        colour="blue",
        smoothing=0.5,
        position=3,
    )

    assert not bar.leave
    assert not bar.disable
    assert bar.ncols == 120
    assert bar.colour == "blue"
    assert bar.smoothing == 0.1
    assert bar.pos == -3

    # takes next available position
    bar = logger.get_progress_bar(iterable=range(0, 50))
    assert bar.pos == -4

    for bar in logger._bars:
        bar.n = bar.total
        bar.close()

    bar = logger.get_progress_bar(
        total=50,
        disable=False,
        file=sys.stderr,
        ncols=500,
        colour="blue",
        smoothing=0.5,
    )

    assert logger._bars == [bar]
    assert bar.leave
    assert bar.pos == 0

    logger.disable_bars = True


def test_copy(logger: MusifyLogger):
    assert id(copy(logger)) == id(logger)
    assert id(deepcopy(logger)) == id(logger)


def test_logger_set():
    assert logging.getLevelName("INFO_EXTRA") == INFO_EXTRA
    assert logging.getLevelName("REPORT") == REPORT
    assert logging.getLevelName("STAT") == STAT

    assert logging.getLoggerClass() == MusifyLogger
    assert isinstance(logging.getLogger(__name__), MusifyLogger)


###########################################################################
## Logging formatters/filters
###########################################################################
def test_format_func_name():
    record = logging.LogRecord(
        name="this.is.a.short",
        level=logging.INFO,
        pathname=__name__,
        lineno=10,
        msg=None,
        args=None,
        exc_info=None,
        func="path",
    )
    format_full_func_name(record=record, width=20)
    assert record.funcName == "this.is.a.short.path"

    record.name = "this.is.quite.a.long"
    record.funcName = "path"
    format_full_func_name(record=record, width=20)
    assert record.funcName == "t.i.q.a.long.path"

    record.name = "this.path.has.a.ClassName"
    record.funcName = "in_it"
    format_full_func_name(record=record, width=20)
    assert record.funcName == "t.p.h.a.CN.in_it"


def test_file_filter():
    log_filter = LogFileFilter(name="test")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__name__,
        lineno=10,
        msg=None,
        args=None,
        exc_info=None,
        func="function_name"
    )

    record.msg = "normal message"
    log_filter.filter(record)
    assert record.msg == "normal message"

    # noinspection SpellCheckingInspection
    record.msg = "\33[91;1mcolour \33[94;0mmessage\33[0m"
    log_filter.filter(record)
    assert record.msg == "colour message"


###########################################################################
## Logging handlers
###########################################################################
def test_current_time_file_handler_namer():
    # no filename given
    handler = CurrentTimeRotatingFileHandler(delay=True)
    assert handler.filename == join(PACKAGE_ROOT, handler.dt.strftime(LOGGING_DT_FORMAT) + ".log")

    # no format part given
    handler = CurrentTimeRotatingFileHandler(filename="test.log", delay=True)
    assert handler.filename == join(PACKAGE_ROOT, "test.log")

    # filename with format part given and fixes separators
    sep = "\\" if os.path.sep == "/" else "/"
    base_parts = ["folder", "file_{}_suffix.log"]
    base_str = sep.join(base_parts)

    handler = CurrentTimeRotatingFileHandler(filename=base_str, delay=True)
    assert handler.filename == join(
        PACKAGE_ROOT, os.path.sep.join(base_parts).format(handler.dt.strftime(LOGGING_DT_FORMAT))
    )

    base_parts[1] = base_parts[1].format(handler.dt.strftime(LOGGING_DT_FORMAT))
    assert sep not in handler.filename
    assert handler.filename.split(os.path.sep) == PACKAGE_ROOT.split(os.path.sep) + base_parts


@pytest.fixture
def log_paths(tmp_path: str) -> list[str]:
    """Generate a set of log files and return their paths"""
    dt_now = datetime.now()

    paths = []
    for i in range(1, 50, 2):
        dt_str = (dt_now - timedelta(hours=i)).strftime(LOGGING_DT_FORMAT)
        path = join(tmp_path, dt_str + ".log")
        paths.append(path)

        with open(path, 'w') as f:
            for _ in range(600):
                f.write(choice(string.ascii_letters))

    return paths


def test_current_time_file_handler_rotator_time(log_paths: list[str], tmp_path: str):
    handler = CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}.log"), when="h", interval=10)

    for dt in handler.removed:
        assert dt < handler.dt - timedelta(hours=10)
    for path in glob(join(tmp_path, "*")):
        dt = datetime.strptime(splitext(basename(path))[0], LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)


def test_current_time_file_handler_rotator_count(log_paths: list[str], tmp_path: str):
    CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}.log"), count=10)
    assert len(glob(join(tmp_path, "*"))) == 10


def test_current_time_file_handler_rotator_combined(log_paths: list[str], tmp_path: str):
    handler = CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}.log"), when="h", interval=10, count=3)

    for path in glob(join(tmp_path, "*")):
        dt = datetime.strptime(splitext(basename(path))[0], LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)

    assert len(glob(join(tmp_path, "*"))) <= 3


def test_current_time_file_handler_rotator_folders(tmp_path: str):
    dt_now = datetime.now()

    paths = []
    for i in range(1, 50, 2):
        dt_str = (dt_now - timedelta(hours=i)).strftime(LOGGING_DT_FORMAT)
        path = join(tmp_path, dt_str)
        paths.append(path)
        os.makedirs(path)

        if i > 10:  # all folders with dt >10hrs will be empty
            continue

        with open(join(path, random_str() + ".txt"), 'w') as f:
            for _ in range(600):
                f.write(choice(string.ascii_letters))

    handler = CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}"), when="h", interval=20)

    for path in glob(join(tmp_path, "*")):
        dt = datetime.strptime(basename(path), LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)  # deleted all empty folders >10hrs
