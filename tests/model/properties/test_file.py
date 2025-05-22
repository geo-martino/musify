from collections.abc import Iterator, Collection
from pathlib import PurePosixPath, Path, PureWindowsPath, PurePath
from random import choice
from typing import Literal

import pytest
from faker import Faker

from musify.model.properties.file import _IsFile, PathMapper, PathStemMapper


def _get_file_paths(faker: Faker, system: Literal["linux", "windows"] = "linux", count: int = 20) -> Iterator[PurePath]:
    path_iter = (faker.file_path(depth=4, category="audio", file_system_rule=system) for _ in range(count))
    return map(PurePosixPath, path_iter) if system == "linux" else map(PureWindowsPath, path_iter)


def _get_directory_paths(faker: Faker, system: Literal["linux", "windows"] = "linux", count: int = 20) -> Iterator[PurePath]:
    return (path.parent for path in _get_file_paths(faker, system=system, count=count))


class TestPathMapper:
    @pytest.fixture
    def model(self, faker: Faker) -> PathMapper:
        return PathMapper()

    def test_map(self, model: PathMapper, faker: Faker):
        expected = list(map(str, _get_file_paths(faker)))
        files = [choice([path, _IsFile(path=path)]) for path in expected]

        # all mapping functions produce same results
        assert [model.map(file, check_existence=False) for file in files] == expected
        assert model.map_many(files, check_existence=False) == expected
        assert [model.unmap(file, check_existence=False) for file in files] == expected
        assert model.unmap_many(files, check_existence=False) == expected

    def test_checks_existence_on_non_existing_files(self, model: PathMapper, faker: Faker):
        files = [choice([str(path), _IsFile(path=path)]) for path in _get_file_paths(faker)]

        assert not any(model.map(file, check_existence=True) for file in files)
        assert not any(model.unmap(file, check_existence=True) for file in files)
        assert not model.map_many(files, check_existence=True)
        assert not model.unmap_many(files, check_existence=True)

    def test_checks_existence_on_existing_files(self, model: PathMapper, faker: Faker, tmp_path: Path):
        files = [choice([str(path), _IsFile(path=path)]) for path in _get_file_paths(faker)]
        existing_files = [
            tmp_path.with_name(faker.file_name(category="audio")) for _ in range(faker.random_int(5, 8))
        ]
        for path in existing_files:
            path.touch(exist_ok=True)

        result = set(model.map_many(files + existing_files, check_existence=True))
        assert result == set(map(str, existing_files))


class TestPathStemMapper(TestPathMapper):

    @pytest.fixture
    def model(self, faker: Faker) -> PathStemMapper:
        stem_map = dict(zip(_get_directory_paths(faker, "windows"), _get_directory_paths(faker, "linux")))
        available_paths = map(str, (path.joinpath(faker.file_name(category="audio")) for path in stem_map))

        stem_map = dict(list(map(str, item)) for item in stem_map.items())
        available_paths = {path.casefold(): path for path in available_paths}
        return PathStemMapper(stem_map=stem_map, available_paths=available_paths)

    # noinspection PyTypeChecker
    def test_map_available_paths_iter(self, model: PathStemMapper, faker: Faker):
        paths = list(map(str, _get_file_paths(faker, "windows")))

        model.available_paths = paths[0]
        assert model.available_paths == {paths[0].casefold(): paths[0]}

        model.available_paths = paths
        assert model.available_paths == {path.casefold(): path for path in paths}

    # noinspection PyTypeChecker
    def test_map_stem_map_iter(self, model: PathStemMapper, faker: Faker):
        paths = list(
            tuple(map(str, item))
            for item in zip(_get_directory_paths(faker, "windows"), _get_directory_paths(faker, "linux"))
        )

        model.stem_map = paths
        assert model.stem_map == dict(paths)

        model.stem_map = [(PureWindowsPath(k), PurePosixPath(v)) for k, v in paths]
        assert model.stem_map == dict(paths)

    def test_stem_map_reversed(self, model: PathStemMapper):
        assert model.stem_map
        assert model.stem_map_reversed == {v: k for k, v in model.stem_map.items()}

    def test_fixes_cases_using_available_paths(self, model: PathStemMapper):
        model.stem_map.clear()
        assert len(model.available_paths) > 3
        available_paths = list(model.available_paths.values())

        assert model.map_many([path.upper() for path in available_paths], check_existence=False) == available_paths
        assert model.map_many([path.lower() for path in available_paths], check_existence=False) == available_paths

    def test_replaces_stems(self, model: PathStemMapper):
        paths = list(model.available_paths.values())
        self.assert_reversable_stem_mapping(model=model, paths=paths, expected=model.available_paths.values())

    def test_combined(self, model: PathStemMapper):
        paths = [path.upper() for path in model.available_paths]
        self.assert_reversable_stem_mapping(model=model, paths=paths, expected=model.available_paths.values())

    def assert_reversable_stem_mapping(self, model: PathStemMapper, paths: Collection[str], expected: Collection[str]):
        assert len(model.stem_map) > 3
        assert len(model.available_paths) > 3
        assert len(paths) > 3

        results = model.map_many(paths, check_existence=False)
        assert len(results) == len(paths)
        for path in results:
            assert any(path.startswith(stem) for stem in model.stem_map.values())
            assert all(not path.startswith(stem) for stem in model.stem_map)
            assert "\\" not in path

        assert model.unmap_many([path.lower() for path in paths], check_existence=False) == list(expected)
