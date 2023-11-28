from .m3u import M3U
from .xautopf import XAutoPF
from .playlist import LocalPlaylist

__PLAYLIST_CLASSES__ = {M3U, XAutoPF}
__PLAYLIST_FILETYPES__ = {filetype for c in __PLAYLIST_CLASSES__ for filetype in c.valid_extensions}
