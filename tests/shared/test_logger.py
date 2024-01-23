import logging
from copy import copy, deepcopy
from os.path import basename

import pytest
import sys

from musify.shared.logger import MusifyLogger, INFO_EXTRA, REPORT, STAT
from musify.shared.logger import format_full_func_name, LogFileFilter


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
