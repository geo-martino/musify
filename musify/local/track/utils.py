"""
Utilities for operations on :py:class:`LocalTrack` types.

Generally, this will contain global variables representing all supported audio file types
and a utility function for loading the appropriate :py:class:`LocalTrack` type for a path based on its extension.
"""

from os.path import splitext

from musify.local.exception import InvalidFileType
from musify.local.track import LocalTrack
from musify.local.track.flac import FLAC
from musify.local.track.m4a import M4A
from musify.local.track.mp3 import MP3
from musify.local.track.wma import WMA
from musify.shared.remote.processors.wrangle import RemoteDataWrangler

TRACK_CLASSES = frozenset({FLAC, MP3, M4A, WMA})
TRACK_FILETYPES = frozenset(filetype for c in TRACK_CLASSES for filetype in c.valid_extensions)


def load_track(path: str, remote_wrangler: RemoteDataWrangler = None) -> LocalTrack:
    """
    Attempt to load a file from a given path, returning the appropriate :py:class:`LocalTrack` object

    :param path: The path of the file to load.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute on the track object.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    :return: Loaded :py:class:`LocalTrack` object
    :raise InvalidFileType: If the file type is not supported.
    """
    ext = splitext(path)[1].casefold()

    if ext in FLAC.valid_extensions:
        return FLAC(file=path, remote_wrangler=remote_wrangler)
    elif ext in MP3.valid_extensions:
        return MP3(file=path, remote_wrangler=remote_wrangler)
    elif ext in M4A.valid_extensions:
        return M4A(file=path, remote_wrangler=remote_wrangler)
    elif ext in WMA.valid_extensions:
        return WMA(file=path, remote_wrangler=remote_wrangler)

    raise InvalidFileType(
        ext, f"Not an accepted extension. Use only: {', '.join(TRACK_FILETYPES)}"
    )
