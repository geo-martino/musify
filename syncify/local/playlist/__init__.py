from collections.abc import Iterable, Collection
from os.path import splitext

from syncify.local.exception import InvalidFileType
from syncify.local.playlist.match import LocalMatcher
from syncify.local.track import LocalTrack
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitCollection
from .m3u import M3U
from .playlist import LocalPlaylist
from .xautopf import XAutoPF

__PLAYLIST_CLASSES__ = frozenset({M3U, XAutoPF})
__PLAYLIST_FILETYPES__ = frozenset(filetype for c in __PLAYLIST_CLASSES__ for filetype in c.valid_extensions)


def load_playlist(
        path: str,
        tracks: Collection[LocalTrack] = (),
        library_folder: str | None = None,
        other_folders: UnitCollection[str] = (),
        check_existence: bool = True,
        available_track_paths: Iterable[str] = (),
        remote_wrangler: RemoteDataWrangler = None,
) -> LocalPlaylist:
    """
    Attempt to load a file from a given path, returning the appropriate :py:class:`LocalPlaylist` object

    :param path: Absolute path of the playlist.
        If the playlist ``path`` given does not exist, the playlist instance will use all the tracks
        given in ``tracks`` as the tracks in the playlist.
    :param tracks: Optional. Available Tracks to search through for matches.
        If no tracks are given, the playlist instance load all the tracks from paths
        listed in file at the playlist ``path``.
    :param library_folder: Absolute path of folder containing tracks.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param check_existence: If True, when processing paths,
        check for the existence of the file paths on the file system and reject any that don't.
    :param available_track_paths: A list of available track paths that are known to exist
        and are valid for the track types supported by this program.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    :return: Loaded :py:class:`LocalPlaylist` object
    :raise InvalidFileType: If the file type is not supported.
    """
    ext = splitext(path)[1].casefold()

    if ext in M3U.valid_extensions:
        return M3U(
            path=path,
            tracks=tracks,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=check_existence,
            available_track_paths=available_track_paths,
            remote_wrangler=remote_wrangler
        )
    elif ext in XAutoPF.valid_extensions:
        return XAutoPF(
            path=path,
            tracks=tracks,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=check_existence,
            available_track_paths=available_track_paths,
            remote_wrangler=remote_wrangler
        )

    raise InvalidFileType(
        ext, f"Not an accepted extension. Use only: {', '.join(__PLAYLIST_FILETYPES__)}"
    )

