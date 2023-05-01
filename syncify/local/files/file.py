from os.path import splitext
from typing import Optional

from syncify.local.files.utils.exception import IllegalFileTypeError
from syncify.local.files.flac import FLAC
from syncify.local.files.m4a import M4A
from syncify.local.files.mp3 import MP3
from syncify.local.files.wma import WMA


def load_track(path: str, position: Optional[int] = None):
    ext = splitext(path)[1].lower()
    track_classes = [FLAC, MP3, M4A, WMA]

    if ext in FLAC.filetypes:
        return FLAC(file=path, position=position)
    elif ext in MP3.filetypes:
        return MP3(file=path, position=position)
    elif ext in M4A.filetypes:
        return M4A(file=path, position=position)
    elif ext in WMA.filetypes:
        return WMA(file=path, position=position)
    else:
        all_filetypes = [filetype for c in track_classes for filetype in c.filetypes]
        raise IllegalFileTypeError(ext, f"Not an accepted extension. Use only: {', '.join(all_filetypes)}")
