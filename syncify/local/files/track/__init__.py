from os.path import splitext
from typing import Optional, Collection

from .base import *
from .collection import *

from .flac import FLAC
from .mp3 import MP3
from .m4a import M4A
from .wma import WMA

__TRACK_CLASSES__ = [FLAC, MP3, M4A, WMA]
__TRACK_FILETYPES__ = [filetype for c in __TRACK_CLASSES__ for filetype in c.valid_extensions]

from syncify.local.files.file import IllegalFileTypeError


def load_track(path: str, available: Optional[Collection[str]] = None) -> LocalTrack:
    """
    Attempt to load a file from a given path, returning the appropriate ``Track`` object

    :param path: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :return: Loaded Track object
    :exception IllegalFileTypeError: If the file type is not supported.
    """
    ext = splitext(path)[1].lower()

    if ext in FLAC.valid_extensions:
        return FLAC(file=path, available=available)
    elif ext in MP3.valid_extensions:
        return MP3(file=path, available=available)
    elif ext in M4A.valid_extensions:
        return M4A(file=path, available=available)
    elif ext in WMA.valid_extensions:
        return WMA(file=path, available=available)
    else:
        all_ext = [ext for c in __TRACK_CLASSES__ for ext in c.valid_extensions]
        raise IllegalFileTypeError(ext, f"Not an accepted extension. Use only: {', '.join(all_ext)}")
