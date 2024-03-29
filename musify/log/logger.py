"""
All classes and operations relating to the logger objects used throughout the entire package.
"""
import logging
import logging.config
import logging.handlers
import os
import sys
from collections.abc import Iterable
from typing import Any

from tqdm.auto import tqdm

from musify.log import INFO_EXTRA, REPORT, STAT


class MusifyLogger(logging.Logger):
    """The logger for all logging operations in Musify."""

    #: When true, never print a new line in the console when :py:meth:`print()` is called
    compact: bool = False
    #: When true, all bars returned by :py:meth:`get_progress_bar()` will be disabled by default
    disable_bars: bool = False
    #: All currently active progress bars
    _bars: list[tqdm] = []

    @property
    def file_paths(self) -> list[str]:
        """Get a list of the paths of all file handlers for this logger"""
        def extract_paths(lggr: logging.Logger) -> None:
            """Extract file path from the handlers of the given ``lggr``"""
            for handler in lggr.handlers:
                if isinstance(handler, logging.FileHandler) and handler.baseFilename not in paths:
                    paths.append(handler.baseFilename)

        paths = []
        logger = self
        extract_paths(logger)
        while logger.propagate and logger.parent:
            logger = logger.parent
            extract_paths(logger)
        return paths

    @property
    def stdout_handlers(self) -> list[logging.StreamHandler]:
        """Get a list of all :py:class:`logging.StreamHandler` handlers that log to stdout"""
        console_handlers = []
        for handler in self.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                console_handlers.append(handler)
        return console_handlers

    def __init__(self, name: str, level: int | str = logging.NOTSET):
        super().__init__(name=name, level=level)

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

    def print(self, level: int = logging.CRITICAL + 1) -> None:
        """Print a new line only when DEBUG < ``logger level`` <= ``level`` for all console handlers"""
        if not self.compact and all(logging.DEBUG < h.level <= level for h in self.stdout_handlers):
            print()

    def get_progress_bar[T: Any](
            self,
            iterable: Iterable[T] | None = None,
            total: T | int | None = None,
            **kwargs
    ) -> tqdm | Iterable[T]:
        """Wrapper for tqdm progress bar. For kwargs, see :py:class:`tqdm_std`"""
        # noinspection SpellCheckingInspection
        preset_keys = ("leave", "disable", "file", "ncols", "colour", "smoothing", "position")

        try:
            cols = os.get_terminal_size().columns
        except OSError:
            cols = 120

        # clear closed bars
        self._bars = [bar for bar in self._bars if bar.n < bar.total]

        # determine the level of bar to generate and whether to leave the bar based on current active count
        position = kwargs.get("position", abs(min(bar.pos for bar in self._bars)) + 1 if self._bars else 0)
        leave_default = all(h.level > logging.DEBUG for h in self.stdout_handlers) and position == 0
        leave = kwargs["leave"] if kwargs.get("leave") is not None else leave_default

        bar = tqdm(
            iterable=iterable,
            total=total,
            leave=leave,
            disable=self.disable_bars or kwargs.get("disable", False),
            file=sys.stdout,
            ncols=cols,
            colour=kwargs.get("colour", "blue"),
            smoothing=0.1,
            position=position,
            **{k: v for k, v in kwargs.items() if k not in preset_keys}
        )
        self._bars.append(bar)
        return bar

    def __copy__(self):
        """Do not copy logger"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy logger"""
        return self


logging.setLoggerClass(MusifyLogger)
