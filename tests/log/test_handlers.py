import os
import string
from datetime import datetime, timedelta
from pathlib import Path
from random import choice

import pytest

from musify.log import LOGGING_DT_FORMAT
from musify.log.handlers import CurrentTimeRotatingFileHandler
from tests.utils import random_str


###########################################################################
## Logging handlers
###########################################################################
def test_current_time_file_handler_namer(tmp_path: Path):
    # no filename given
    handler = CurrentTimeRotatingFileHandler(delay=True)
    assert handler.filename == Path(handler.dt.strftime(LOGGING_DT_FORMAT) + ".log")

    # no format part given
    handler = CurrentTimeRotatingFileHandler(filename="test.log", delay=True)
    assert handler.filename == Path("test.log")

    # filename with format part given and fixes separators
    base_parts = [*str(tmp_path).split(os.path.sep), "folder", "file_{}_suffix.log"]
    base_path = Path(*base_parts)

    handler = CurrentTimeRotatingFileHandler(filename=base_path, delay=True)
    assert handler.filename == Path(str(base_path).format(handler.dt.strftime(LOGGING_DT_FORMAT)))

    sep = "\\" if os.path.sep == "/" else "/"
    assert sep not in str(handler.filename)

    base_parts[-1] = base_parts[-1].format(handler.dt.strftime(LOGGING_DT_FORMAT))
    assert handler.filename.parts == tuple(p for p in base_parts if p)


@pytest.fixture
def log_paths(tmp_path: Path) -> list[Path]:
    """Generate a set of log files and return their paths"""
    dt_now = datetime.now()

    paths = []
    for i in range(1, 50, 2):
        dt_str = (dt_now - timedelta(hours=i)).strftime(LOGGING_DT_FORMAT)
        path = tmp_path.joinpath(dt_str + ".log")
        paths.append(path)

        with open(path, "w") as f:
            for _ in range(600):
                f.write(choice(string.ascii_letters))

    return paths


def test_current_time_file_handler_rotator_time(log_paths: list[str], tmp_path: Path):
    filename = tmp_path.joinpath("{}.log")
    handler = CurrentTimeRotatingFileHandler(filename=filename, when="h", interval=10)

    for dt in handler.removed:
        assert dt < handler.dt - timedelta(hours=10)
    for path in tmp_path.glob("*"):
        dt = datetime.strptime(path.stem, LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)


def test_current_time_file_handler_rotator_count(log_paths: list[str], tmp_path: Path):
    filename = tmp_path.joinpath("{}.log")
    CurrentTimeRotatingFileHandler(filename=filename, count=10)
    assert len(list(tmp_path.glob("*"))) == 10


def test_current_time_file_handler_rotator_combined(log_paths: list[str], tmp_path: Path):
    filename = tmp_path.joinpath("{}.log")
    handler = CurrentTimeRotatingFileHandler(filename=filename, when="h", interval=10, count=3)

    for path in tmp_path.glob("*"):
        dt = datetime.strptime(path.stem, LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)

    assert len(list(tmp_path.glob("*"))) <= 3


def test_current_time_file_handler_rotator_folders(tmp_path: Path):
    dt_now = datetime.now()

    paths = []
    for i in range(1, 50, 2):
        dt_str = (dt_now - timedelta(hours=i)).strftime(LOGGING_DT_FORMAT)
        path = tmp_path.joinpath(dt_str)
        paths.append(path)
        os.makedirs(path)

        if i > 10:  # all folders with dt >10hrs will be empty
            continue

        with open(path.joinpath(random_str() + ".txt"), "w") as f:
            for _ in range(600):
                f.write(choice(string.ascii_letters))

    handler = CurrentTimeRotatingFileHandler(filename=tmp_path.joinpath("{}"), when="h", interval=20)

    for path in tmp_path.glob("*"):
        dt = datetime.strptime(path.name, LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)  # deleted all empty folders >10hrs
