from collections.abc import Iterable
from os.path import basename, splitext, dirname
from random import randrange

import pytest

from syncify.local.library import LocalLibrary
from syncify.local.track import LocalTrack
from tests.local.library.utils import LocalLibraryTester
from tests.local.playlist.utils import path_playlist_resources, path_playlist_m3u
from tests.local.playlist.utils import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.utils import path_track_resources, path_track_all, random_tracks, random_track


class TestLocalLibrary(LocalLibraryTester):

    @pytest.fixture
    def library(self) -> LocalLibrary:
        library = LocalLibrary(library_folder=path_track_resources, playlist_folder=path_playlist_resources)
        library.load()

        # needed to ensure __setitem__ check passes
        library.items.append(random_track(cls=library[0].__class__))
        return library

    @pytest.fixture
    def collection_merge_items(self) -> Iterable[LocalTrack]:
        return random_tracks(randrange(5, 10))

    @pytest.fixture(scope="class")
    def blank_library(self) -> LocalLibrary:
        return LocalLibrary()

    def test_init_include(self):
        library_include = LocalLibrary(
            library_folder=path_track_resources,
            playlist_folder=path_playlist_resources,
            include=[splitext(basename(path_playlist_m3u))[0], splitext(basename(path_playlist_xautopf_bp))[0]],
        )
        assert library_include.library_folder == path_track_resources
        assert library_include._track_paths == path_track_all
        assert library_include.playlist_folder == path_playlist_resources
        assert library_include._playlist_paths == {
            splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
            splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
        }

    def test_init_exclude(self):
        library_exclude = LocalLibrary(
            library_folder=path_track_resources,
            playlist_folder=path_playlist_resources,
            exclude=[splitext(basename(path_playlist_xautopf_bp))[0]],
        )
        assert library_exclude.playlist_folder == path_playlist_resources
        assert library_exclude._playlist_paths == {
            splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
            splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
        }

    def test_init_relative_paths(self):
        library_relative_paths = LocalLibrary(
            library_folder=dirname(path_playlist_resources),
            playlist_folder=basename(path_playlist_resources),
        )
        assert len(library_relative_paths._track_paths) == 6
        assert library_relative_paths.playlist_folder == path_playlist_resources
        assert library_relative_paths._playlist_paths == {
            splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
            splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
            splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
        }

    def test_load(self):
        library = LocalLibrary(
            library_folder=path_track_resources,
            playlist_folder=path_playlist_resources,
        )
        library.load()
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
