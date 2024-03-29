"""
All classes and functions pertaining to logging operations throughout the package.
"""
import logging

LOGGING_DT_FORMAT = "%Y-%m-%d_%H.%M.%S"

INFO_EXTRA = logging.INFO - 1
logging.addLevelName(INFO_EXTRA, "INFO_EXTRA")
logging.INFO_EXTRA = INFO_EXTRA

REPORT = logging.INFO - 3
logging.addLevelName(REPORT, "REPORT")
logging.REPORT = REPORT

STAT = logging.DEBUG + 3
logging.addLevelName(STAT, "STAT")
logging.STAT = STAT
