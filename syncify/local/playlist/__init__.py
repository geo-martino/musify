from .m3u import M3U
from .playlist import LocalPlaylist
from .xautopf import XAutoPF

__PLAYLIST_CLASSES__ = frozenset({M3U, XAutoPF})
__PLAYLIST_FILETYPES__ = frozenset(filetype for c in __PLAYLIST_CLASSES__ for filetype in c.valid_extensions)
