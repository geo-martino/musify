from random import choice

import pytest

from musify.file.base import File
from musify.file.path_mapper import PathMapper, PathStemMapper
from tests.core.printer import PrettyPrinterTester
from tests.libraries.local.track.utils import random_tracks
from tests.libraries.local.utils import path_track_all
from tests.utils import random_str


class TestPathMapper(PrettyPrinterTester):
    @pytest.fixture
    def obj(self) -> PathMapper:
        return PathMapper()

    def test_map(self, obj: PathMapper):
        tracks = random_tracks(30) + [f"D:\\{random_str(5, 30)}\\{random_str(30, 50)}.MP3" for _ in range(20)]
        expected = [track.path if isinstance(track, File) else track for track in tracks]

        # all mapping functions produce same results
        assert [obj.map(track, check_existence=False) for track in tracks] == expected
        assert obj.map_many(tracks, check_existence=False) == expected
        assert [obj.unmap(track, check_existence=False) for track in tracks] == expected
        assert obj.unmap_many(tracks, check_existence=False) == expected

    def test_checks_existence(self, obj: PathStemMapper):
        # none of these paths exist so all return nothing
        tracks = random_tracks(30) + [f"D:\\{random_str(5, 30)}\\{random_str(30, 50)}.MP3" for _ in range(20)]
        assert not any(obj.map(track, check_existence=True) for track in tracks)
        assert not any(obj.unmap(track, check_existence=True) for track in tracks)
        assert not obj.map_many(tracks, check_existence=True)
        assert not obj.unmap_many(tracks, check_existence=True)

        assert set(obj.map_many(path_track_all | set(tracks), check_existence=True)) == path_track_all


class TestPathStemMapper(PrettyPrinterTester):

    @pytest.fixture
    def obj(self) -> PathStemMapper:
        stem_map = {f"D:\\{random_str(5, 30)}": f"/{random_str(5, 30)}/{random_str(5, 30)}" for _ in range(20)}
        available_paths = [f"{choice(list(stem_map))}\\{random_str(30, 50)}.MP3" for _ in range(20)]
        return PathStemMapper(stem_map=stem_map, available_paths=available_paths)

    def test_checks_existence(self, obj: PathStemMapper):
        # none of these paths exist so all return nothing
        available_paths = list(obj.available_paths.values())
        assert not any(obj.map(path, check_existence=True) for path in available_paths)
        assert not any(obj.unmap(path, check_existence=True) for path in available_paths)
        assert not obj.map_many(available_paths, check_existence=True)
        assert not obj.unmap_many(available_paths, check_existence=True)

        assert set(obj.map_many(path_track_all | set(available_paths), check_existence=True)) == path_track_all

    def test_fixes_cases(self, obj: PathStemMapper):
        obj.stem_map.clear()
        obj.stem_unmap.clear()
        available_paths = list(obj.available_paths.values())

        assert obj.map_many([path.upper() for path in available_paths], check_existence=False) == available_paths
        assert obj.map_many([path.lower() for path in available_paths], check_existence=False) == available_paths

    def test_replaces_stems(self, obj: PathStemMapper):
        available_paths = list(obj.available_paths.values())

        results = obj.map_many(available_paths, check_existence=False)
        for path in results:
            assert any(path.startswith(stem) for stem in obj.stem_map.values())
            assert all(not path.startswith(stem) for stem in obj.stem_map)
            assert "\\" not in path

        assert obj.unmap_many(results, check_existence=False) == available_paths

    def test_combined(self, obj: PathStemMapper):
        available_paths = list(obj.available_paths.values())

        results = obj.map_many([path.upper() for path in available_paths], check_existence=False)
        for path in results:
            assert any(path.startswith(stem) for stem in obj.stem_map.values())
            assert all(not path.startswith(stem) for stem in obj.stem_map)
            assert "\\" not in path

        assert obj.unmap_many([path.lower() for path in available_paths], check_existence=False) == available_paths
