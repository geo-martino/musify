from os.path import basename, splitext

from syncify.local.library import LocalLibrary
from tests.local import remote_wrangler
from tests.local.playlist import path_playlist_resources, path_playlist_m3u
from tests.local.playlist import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.track import path_track_m4a, path_track_wma
from tests.local.track import path_track_resources, path_track_flac, path_track_mp3


def test_init():
    library_blank = LocalLibrary(load=False, remote_wrangler=remote_wrangler)

    assert library_blank.library_folder is None
    assert len(library_blank._track_paths) == 0
    library_blank.library_folder = path_track_resources
    assert library_blank.library_folder == path_track_resources
    assert library_blank._track_paths == {path_track_flac, path_track_mp3, path_track_m4a, path_track_wma}

    assert library_blank.playlist_folder is None
    assert library_blank._playlist_paths is None
    library_blank.playlist_folder = path_playlist_resources
    assert library_blank.playlist_folder == path_playlist_resources
    assert library_blank._playlist_paths == {
        splitext(basename(path_playlist_m3u).lower())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp).lower())[0]: path_playlist_xautopf_bp,
        splitext(basename(path_playlist_xautopf_ra).lower())[0]: path_playlist_xautopf_ra,
    }

    library_include = LocalLibrary(
        library_folder=path_track_resources,
        playlist_folder=path_playlist_resources,
        include=[splitext(basename(path_playlist_m3u))[0], splitext(basename(path_playlist_xautopf_bp))[0]],
        load=False,
        remote_wrangler=remote_wrangler,
    )
    assert library_include.library_folder == path_track_resources
    assert library_include._track_paths == {path_track_flac, path_track_mp3, path_track_m4a, path_track_wma}
    assert library_include.playlist_folder == path_playlist_resources
    assert library_include._playlist_paths == {
        splitext(basename(path_playlist_m3u).lower())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp).lower())[0]: path_playlist_xautopf_bp,
    }

    library_exclude = LocalLibrary(
        library_folder=path_track_resources,
        playlist_folder=path_playlist_resources,
        exclude=[splitext(basename(path_playlist_xautopf_bp))[0]],
        load=False,
        remote_wrangler=remote_wrangler,
    )
    assert library_exclude.playlist_folder == path_playlist_resources
    assert library_exclude._playlist_paths == {
        splitext(basename(path_playlist_m3u).lower())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_ra).lower())[0]: path_playlist_xautopf_ra,
    }


def test_load():
    library = LocalLibrary(
        library_folder=path_track_resources,
        playlist_folder=path_playlist_resources,
        remote_wrangler=remote_wrangler,
    )
    tracks = {track.path for track in library.tracks}
    playlists = {name: pl.path for name, pl in library.playlists.items()}

    assert tracks == {path_track_flac, path_track_mp3, path_track_m4a, path_track_wma}
    assert playlists == {
        splitext(basename(path_playlist_m3u))[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp))[0]: path_playlist_xautopf_bp,
        splitext(basename(path_playlist_xautopf_ra))[0]: path_playlist_xautopf_ra,
    }

    assert library.last_played is None
    assert library.last_added is None
    assert library.last_modified == max(track.date_modified for track in library.tracks)
