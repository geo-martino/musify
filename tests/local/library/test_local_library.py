from os.path import basename, splitext, dirname

from syncify.local.library import LocalLibrary
from tests.abstract.misc import pretty_printer_tests
from tests.local.library import init_blank_test
from tests.local.playlist import path_playlist_resources, path_playlist_m3u
from tests.local.playlist import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.track import path_track_resources, path_track_all


def test_init():
    init_blank_test(LocalLibrary(load=False))

    library_include = LocalLibrary(
        library_folder=path_track_resources,
        playlist_folder=path_playlist_resources,
        include=[splitext(basename(path_playlist_m3u))[0], splitext(basename(path_playlist_xautopf_bp))[0]],
        load=False,
    )
    assert library_include.library_folder == path_track_resources
    assert library_include._track_paths == path_track_all
    assert library_include.playlist_folder == path_playlist_resources
    assert library_include._playlist_paths == {
        splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
    }

    pretty_printer_tests(library_include, dict_json_equal=False)

    library_exclude = LocalLibrary(
        library_folder=path_track_resources,
        playlist_folder=path_playlist_resources,
        exclude=[splitext(basename(path_playlist_xautopf_bp))[0]],
        load=False,
    )
    assert library_exclude.playlist_folder == path_playlist_resources
    assert library_exclude._playlist_paths == {
        splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
    }

    pretty_printer_tests(library_exclude, dict_json_equal=False)

    library_relative_paths = LocalLibrary(
        library_folder=dirname(path_playlist_resources),
        playlist_folder=basename(path_playlist_resources),
        load=False,
    )
    assert len(library_relative_paths._track_paths) == 6
    assert library_relative_paths.playlist_folder == path_playlist_resources
    assert library_relative_paths._playlist_paths == {
        splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
        splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
    }

    pretty_printer_tests(library_relative_paths, dict_json_equal=False)


def test_load():
    library = LocalLibrary(
        library_folder=path_track_resources,
        playlist_folder=path_playlist_resources,
    )
    tracks = {track.path for track in library.tracks}
    playlists = {name: pl.path for name, pl in library.playlists.items()}

    assert tracks == path_track_all
    assert playlists == {
        splitext(basename(path_playlist_m3u))[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp))[0]: path_playlist_xautopf_bp,
        splitext(basename(path_playlist_xautopf_ra))[0]: path_playlist_xautopf_ra,
    }

    assert library.last_played is None
    assert library.last_added is None
    assert library.last_modified == max(track.date_modified for track in library.tracks)
