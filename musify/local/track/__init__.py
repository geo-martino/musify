"""
Operations relating to reading and writing tags/metadata/properties to various types of audio files.

Specific audio file types should implement :py:class:`LocalTrack`.
"""

from .base.track import LocalTrack
from .base.writer import SyncResultTrack
from .flac import FLAC
from .m4a import M4A
from .mp3 import MP3
from .utils import TRACK_CLASSES, TRACK_FILETYPES, load_track
from .wma import WMA
