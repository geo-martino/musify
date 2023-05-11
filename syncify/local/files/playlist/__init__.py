from .playlist import LocalPlaylist
from .m3u import M3U, SyncResultM3U
from .xautopf import XAutoPF, SyncResultXAutoPF

__PLAYLIST_CLASSES__ = [M3U, XAutoPF]
__PLAYLIST_FILETYPES__ = [filetype for c in __PLAYLIST_CLASSES__ for filetype in c.valid_extensions]
