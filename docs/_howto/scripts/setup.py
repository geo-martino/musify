import logging
import sys

from musify.log import STAT

logging.basicConfig(format="%(message)s", level=STAT, stream=sys.stdout)
