from collections.abc import Iterable
from os.path import splitext

from syncify.local.exception import InvalidFileType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from ._base import LocalTrack
from ._flac import FLAC
from ._m4a import M4A
from ._mp3 import MP3
from ._wma import WMA

TRACK_CLASSES = frozenset({FLAC, MP3, M4A, WMA})
TRACK_FILETYPES = frozenset(filetype for c in TRACK_CLASSES for filetype in c.valid_extensions)


def load_track(path: str, available: Iterable[str] = (), remote_wrangler: RemoteDataWrangler = None) -> LocalTrack:
    """
    Attempt to load a file from a given path, returning the appropriate :py:class:`LocalTrack` object

    :param path: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist
        and are valid for the track types supported by this program.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute on the track object.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    :return: Loaded :py:class:`LocalTrack` object
    :raise InvalidFileType: If the file type is not supported.
    """
    ext = splitext(path)[1].casefold()

    if ext in FLAC.valid_extensions:
        return FLAC(file=path, available=available, remote_wrangler=remote_wrangler)
    elif ext in MP3.valid_extensions:
        return MP3(file=path, available=available, remote_wrangler=remote_wrangler)
    elif ext in M4A.valid_extensions:
        return M4A(file=path, available=available, remote_wrangler=remote_wrangler)
    elif ext in WMA.valid_extensions:
        return WMA(file=path, available=available, remote_wrangler=remote_wrangler)

    raise InvalidFileType(
        ext, f"Not an accepted extension. Use only: {', '.join(TRACK_FILETYPES)}"
    )
