from collections.abc import Iterable
from random import randrange

import pytest

from musify.file.path_mapper import PathMapper, PathStemMapper
from musify.libraries.local.library import LocalLibrary
from musify.libraries.local.playlist import PLAYLIST_CLASSES
from musify.libraries.local.track import LocalTrack
from musify.processors.filter import FilterDefinedList, FilterIncludeExclude
from tests.libraries.local.library.testers import LocalLibraryTester
from tests.libraries.local.track.utils import random_track, random_tracks
from tests.libraries.local.utils import path_playlist_m3u, path_playlist_xautopf_bp
from tests.libraries.local.utils import path_playlist_resources, path_playlist_all
from tests.libraries.local.utils import path_track_resources, path_track_all
from tests.utils import path_resources


class TestLocalLibrary(LocalLibraryTester):

    @pytest.fixture
    async def library(self) -> LocalLibrary:
        library = LocalLibrary(library_folders=path_resources, playlist_folder=path_playlist_resources)
        await library.load()

        # needed to ensure __setitem__ check passes
        library.items.append(random_track(cls=library[0].__class__))
        return library

    @pytest.fixture
    def collection_merge_items(self) -> Iterable[LocalTrack]:
        return random_tracks(randrange(5, 10))

    def test_library(self) -> None:
        library = LocalLibrary()
        assert not library.library_folders
        assert len(library._track_paths) == 0

        library.library_folders = path_track_resources
        assert library.library_folders == [path_track_resources]
        assert library._track_paths == path_track_all

        assert library.playlist_folder is None
        assert not library._playlist_paths

        library.playlist_folder = path_playlist_resources
        assert library.playlist_folder == path_playlist_resources
        assert library._playlist_paths == {path.stem: path for path in path_playlist_all}

    def test_init_include(self):
        library = LocalLibrary(
            library_folders=path_track_resources,
            playlist_folder=path_playlist_resources,
            playlist_filter=FilterDefinedList([path_playlist_m3u.stem, path_playlist_xautopf_bp.stem]),
        )
        assert library.library_folders == [path_track_resources]
        assert library._track_paths == path_track_all
        assert library.playlist_folder == path_playlist_resources

        expected_playlists = {
            pl.stem: pl for pl in [path_playlist_m3u, path_playlist_xautopf_bp]
            if any(pl.suffix == ext for cls in PLAYLIST_CLASSES for ext in cls.valid_extensions)
        }
        assert library._playlist_paths == expected_playlists

    def test_init_exclude(self, path_mapper: PathStemMapper):
        library = LocalLibrary(
            library_folders=path_track_resources,
            playlist_folder=path_playlist_resources,
            playlist_filter=FilterIncludeExclude(
                include=FilterDefinedList(),
                exclude=FilterDefinedList([path_playlist_xautopf_bp.stem])
            ),
            path_mapper=path_mapper,
        )

        assert set(path_mapper.available_paths.values()) == set(map(str, library._track_paths))

        assert library.playlist_folder == path_playlist_resources
        assert library._playlist_paths == {
            path.stem: path for path in path_playlist_all if path != path_playlist_xautopf_bp
        }

    def test_init_relative_paths(self):
        library_relative_paths = LocalLibrary(
            library_folders=path_resources, playlist_folder=path_playlist_resources.name,
        )
        assert len(library_relative_paths._track_paths) == 6
        assert library_relative_paths.playlist_folder == path_playlist_resources
        assert library_relative_paths._playlist_paths == {
            path.stem: path for path in path_playlist_all
        }

    def test_collection_creators(self, library: LocalLibrary):
        assert len(library.folders) == len(set(track.folder for track in library.tracks))
        assert len(library.albums) == len(set(track.album for track in library.tracks))
        assert len(library.artists) == len(set(artist for track in library.tracks for artist in track.artists))
        assert len(library.genres) == len(set(genre for track in library.tracks for genre in track.genres))

    async def test_load(self, path_mapper: PathMapper):
        library = LocalLibrary(
            library_folders=path_track_resources, playlist_folder=path_playlist_resources, path_mapper=path_mapper
        )
        await library.load()
        tracks = {track.path for track in library.tracks}
        playlists = {name: pl.path for name, pl in library.playlists.items()}

        assert tracks == library._track_paths == path_track_all
        assert playlists == {path.stem: path for path in path_playlist_all}
        assert all(pl.path_mapper == path_mapper for pl in library.playlists.values())

        assert library.last_played is None
        assert library.last_added is None
        assert library.last_modified == max(track.date_modified for track in library.tracks)

        library.library_folders = [path_track_resources, path_playlist_resources]
        await library.load()

        assert len(library.tracks) == len(library._track_paths) == len(path_track_all) + 2
