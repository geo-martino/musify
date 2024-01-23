"""
All logging handlers specific to this package.
"""

import logging.handlers
import os
import shutil
from datetime import datetime
from glob import glob
from os.path import join, dirname, isfile, sep, isdir

from musify.processors.time import TimeMapper
from musify.shared.logger import LOGGING_DT_FORMAT


###########################################################################
## Logging handlers
###########################################################################
class CurrentTimeRotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """
    Handles log file and directory rotation based on log file/folder name.

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
        if dirname(self.filename):
            os.makedirs(dirname(self.filename), exist_ok=True)

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
