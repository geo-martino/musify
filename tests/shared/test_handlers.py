import os
import string
from datetime import datetime, timedelta
from glob import glob
from os.path import join, basename, splitext
from pathlib import Path
from random import choice

import pytest

from musify.shared.logger import LOGGING_DT_FORMAT
from musify.shared.handlers import CurrentTimeRotatingFileHandler
from tests.utils import random_str


###########################################################################
## Logging handlers
###########################################################################
def test_current_time_file_handler_namer(tmp_path: Path):
    # no filename given
    handler = CurrentTimeRotatingFileHandler(delay=True)
    assert handler.filename == handler.dt.strftime(LOGGING_DT_FORMAT) + ".log"

    # no format part given
    handler = CurrentTimeRotatingFileHandler(filename="test.log", delay=True)
    assert handler.filename == "test.log"

    # filename with format part given and fixes separators
    sep = "\\" if os.path.sep == "/" else "/"
    base_parts = [*str(tmp_path).split(os.path.sep), "folder", "file_{}_suffix.log"]
    base_str = sep.join(base_parts)

    handler = CurrentTimeRotatingFileHandler(filename=base_str, delay=True)
    assert handler.filename == os.path.sep.join(base_parts).format(handler.dt.strftime(LOGGING_DT_FORMAT))

    base_parts[-1] = base_parts[-1].format(handler.dt.strftime(LOGGING_DT_FORMAT))
    assert sep not in handler.filename
    assert handler.filename.split(os.path.sep) == base_parts


@pytest.fixture
def log_paths(tmp_path: Path) -> list[str]:
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


def test_current_time_file_handler_rotator_time(log_paths: list[str], tmp_path: Path):
    handler = CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}.log"), when="h", interval=10)

    for dt in handler.removed:
        assert dt < handler.dt - timedelta(hours=10)
    for path in glob(join(tmp_path, "*")):
        dt = datetime.strptime(splitext(basename(path))[0], LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)


def test_current_time_file_handler_rotator_count(log_paths: list[str], tmp_path: Path):
    CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}.log"), count=10)
    assert len(glob(join(tmp_path, "*"))) == 10


def test_current_time_file_handler_rotator_combined(log_paths: list[str], tmp_path: Path):
    handler = CurrentTimeRotatingFileHandler(filename=join(tmp_path, "{}.log"), when="h", interval=10, count=3)

    for path in glob(join(tmp_path, "*")):
        dt = datetime.strptime(splitext(basename(path))[0], LOGGING_DT_FORMAT)
        assert dt >= handler.dt - timedelta(hours=10)

    assert len(glob(join(tmp_path, "*"))) <= 3


def test_current_time_file_handler_rotator_folders(tmp_path: Path):
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
