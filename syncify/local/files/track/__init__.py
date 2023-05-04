from os.path import splitext

from .base import *
from .collection import *

from .flac import FLAC
from .mp3 import MP3
from .m4a import M4A
from .wma import WMA

__TRACK_CLASSES__ = [FLAC, MP3, M4A, WMA]
__ACCEPTED_FILETYPES__ = [filetype for c in __TRACK_CLASSES__ for filetype in c.track_ext]

from syncify.local.files.utils.exception import IllegalFileTypeError


def load_track(path: str) -> Track:
    """
    Attempt to load a file from a given path, returning the appropriate ``Track`` object

    :param path: The path or Mutagen object of the file to load.
    :return: Loaded Track object
    :exception IllegalFileTypeError: If the file type is not supported.
    """
    ext = splitext(path)[1].lower()

    if ext in FLAC.track_ext:
        return FLAC(file=path)
    elif ext in MP3.track_ext:
        return MP3(file=path)
    elif ext in M4A.track_ext:
        return M4A(file=path)
    elif ext in WMA.track_ext:
        return WMA(file=path)
    else:
        all_ext = [ext for c in __TRACK_CLASSES__ for ext in c.track_ext]
        raise IllegalFileTypeError(ext, f"Not an accepted extension. Use only: {', '.join(all_ext)}")


if __name__ == "__main__":
    music_folder = "/mnt/d/Music"
    FLAC.set_file_paths(music_folder)
    MP3.set_file_paths(music_folder)
    M4A.set_file_paths(music_folder)
    WMA.set_file_paths(music_folder)

    from pathlib import Path

    paths = [path for clazz in __TRACK_CLASSES__ for path in clazz.available_track_paths]
    print([str(Path(path.upper()).resolve()) for path in paths])

    from timeit import timeit
    print(timeit('[str(Path(path.upper()).resolve()) for path in paths]', number=50, globals=globals()))
