from os.path import splitext
from collections.abc import Collection

from .base.track import LocalTrack
from .flac import FLAC
from .m4a import M4A
from .mp3 import MP3
from .wma import WMA

from syncify.local.exception import IllegalFileTypeError

__TRACK_CLASSES__ = [FLAC, MP3, M4A, WMA]
__TRACK_FILETYPES__ = [filetype for c in __TRACK_CLASSES__ for filetype in c.valid_extensions]


def load_track(path: str, available: Collection[str] | None = None) -> LocalTrack:
    """
    Attempt to load a file from a given path, returning the appropriate ``Track`` object

    :param path: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :return: Loaded Track object
    :raises IllegalFileTypeError: If the file type is not supported.
    """
    ext = splitext(path)[1].casefold()

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
