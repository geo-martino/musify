"""
Operations relating to reading and writing track data and properties to various types of playlist files.

Specific audio file types should implement :py:class:`LocalPlaylist`.
"""
from .base import LocalPlaylist
from .m3u import M3U
from .utils import PLAYLIST_CLASSES, PLAYLIST_FILETYPES, load_playlist
from .xautopf import XAutoPF
