from os.path import basename, splitext, join, dirname

from syncify.local.library.library import LocalLibrary
from tests import path_resources, path_cache
from tests.abstract.misc import pretty_printer_tests
from tests.local.playlist import path_playlist_resources, path_playlist_m3u
from tests.local.playlist import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.track import path_track_resources, path_track_all

path_library_resources = join(path_resources, basename(dirname(__file__)))
path_library_cache = join(path_cache, basename(dirname(__file__)))


# noinspection PyProtectedMember
def init_blank_test(library: LocalLibrary) -> None:
    """General tests to run for every implementation of :py:class:`LocalLibrary`"""
    assert library.library_folder is None
    assert len(library._track_paths) == 0
    library.library_folder = path_track_resources
    assert library.library_folder == path_track_resources
    assert library._track_paths == path_track_all

    assert library.playlist_folder is None
    assert library._playlist_paths is None
    library.playlist_folder = path_playlist_resources
    assert library.playlist_folder == path_playlist_resources
    assert library._playlist_paths == {
        splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
        splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
    }

    pretty_printer_tests(library, dict_json_equal=False)
