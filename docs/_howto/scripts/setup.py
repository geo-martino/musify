import logging
import sys

from musify.logger import STAT

logging.basicConfig(format="%(message)s", level=STAT, stream=sys.stdout)
