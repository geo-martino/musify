from os.path import basename, splitext, dirname

from syncify.local.library import LocalLibrary
from tests.abstract.collection import item_collection_tests, library_tests
from tests.abstract.misc import pretty_printer_tests
from tests.local.library import init_blank_test
from tests.local.playlist import path_playlist_resources, path_playlist_m3u
from tests.local.playlist import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.track import path_track_resources, path_track_all, random_tracks, random_track


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

    # generic item collection and library tests
    # append needed to ensure __setitem__ check passes
    library.items.append(random_track(library[0].__class__))
    item_collection_tests(library, merge_items=random_tracks(5))
    library_tests(library)
    pretty_printer_tests(library, dict_json_equal=False)
