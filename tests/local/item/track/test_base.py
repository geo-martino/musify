from collections.abc import Callable
from datetime import date
from io import BytesIO
from pathlib import Path
from random import choice
from unittest import mock

import mutagen
import pytest
from PIL import Image
from faker import Faker

from musify.local.item.track import LocalTrack
from musify.model import MusifyModel
from musify.model.properties.uri import URI
from tests.model.testers import UniqueKeyTester
from tests.utils import assert_validator_skips


class TestLocalTrack(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return LocalTrack(name=faker.sentence(), uri=uri, path=faker.file_path())

    @pytest.fixture
    def file(self, faker: Faker, tmp_path: Path) -> mutagen.FileType:
        path = tmp_path.joinpath(faker.file_name(category="audio"))

        file = mutagen.FileType()
        file.filename = str(path)
        file.tags = {"name": "Track title"}

        return file

    async def test_from_file(self, file: mutagen.FileType):
        with (
            mock.patch.object(LocalTrack, "_load_mutagen", return_value=file) as mocked_load
        ):
            model = await LocalTrack.from_file(file.filename)
            assert model.name == "Track title"

    async def test_load_mutagen(self, faker: Faker, tmp_path: Path):
        path = tmp_path.joinpath(faker.file_name(category="audio"))
        path.touch()  # needs a real file to open
        file = mutagen.FileType()

        with mock.patch.object(mutagen, "File", return_value=file) as mocked_file:
            result = await LocalTrack._load_mutagen(path)

            mocked_file.assert_called_once()
            assert result is file
            assert result.filename == str(path)

    # noinspection PyCallingNonCallable
    def test_extract_tags_from_mutagen(self, file: mutagen.FileType, faker: Faker):
        tags = faker.pydict()
        file.tags = tags
        assert file.filename

        assert LocalTrack._from_mutagen(tags) is tags
        assert LocalTrack._from_mutagen(file.filename) is file.filename

        result = LocalTrack._from_mutagen(file)
        assert result == tags | dict(path=file.filename)

    # noinspection PyTypeChecker
    def test_extract_tags_from_mutagen_skips(self, faker: Faker):
        assert_validator_skips(LocalTrack._from_mutagen, None)
        assert_validator_skips(LocalTrack._from_mutagen, faker.pyint())
        assert_validator_skips(LocalTrack._from_mutagen, faker.pytuple())
        assert_validator_skips(LocalTrack._from_mutagen, faker.pylist())
        assert_validator_skips(LocalTrack._from_mutagen, faker.pydict())

    def test_extract_first_value_from_sequence(self):
        assert LocalTrack._extract_first_value_from_sequence(None) is None
        assert LocalTrack._extract_first_value_from_sequence("Track name") == "Track name"
        assert LocalTrack._extract_first_value_from_sequence(["Track name"]) == "Track name"

        value = ["Track name", "Artist name"]
        assert LocalTrack._extract_first_value_from_sequence(value) == "Track name"

    def test_extract_first_value_from_sequence_skips(self, faker: Faker):
        assert_validator_skips(LocalTrack._extract_first_value_from_sequence, None)
        assert_validator_skips(LocalTrack._extract_first_value_from_sequence, faker.pystr())
        assert_validator_skips(LocalTrack._extract_first_value_from_sequence, faker.pyint())

    def test_extract_first_value_from_single_sequence(self):
        assert LocalTrack._extract_first_value_from_single_sequence(None) is None
        assert LocalTrack._extract_first_value_from_single_sequence("Track name") == "Track name"
        assert LocalTrack._extract_first_value_from_single_sequence(["Track name"]) == "Track name"

    def test_extract_first_value_from_single_sequence_skips(self, faker: Faker):
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, None)
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pystr())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pyint())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pytuple())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pylist())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pydict())

    def test_nullify(self):
        assert LocalTrack._nullify(None) is None
        assert LocalTrack._nullify([]) is None
        assert LocalTrack._nullify(["", ""]) is None

        expected = ["12", 20]
        assert LocalTrack._nullify(expected) == expected

    def test_nullify_skips(self, faker: Faker):
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, None)
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pystr())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pyint())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pytuple())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pylist())
        assert_validator_skips(LocalTrack._extract_first_value_from_single_sequence, faker.pydict())

    def test_split_joined_tags(self, faker: Faker):
        tags = faker.words(nb=faker.random_int(10, 20))
        sep = choice(LocalTrack._tag_sep)
        tags_joined = [sep.join(tags[:3]), sep.join(tags[3:7]), sep.join(tags[7:])]

        assert LocalTrack._split_joined_tags(tags_joined) == tags

    def test_split_joined_tags_skips(self, faker: Faker):
        assert_validator_skips(LocalTrack._split_joined_tags, None)
        assert_validator_skips(LocalTrack._split_joined_tags, faker.pyint())
        assert_validator_skips(LocalTrack._split_joined_tags, faker.pytuple())
        assert_validator_skips(LocalTrack._split_joined_tags, faker.pylist())
        assert_validator_skips(LocalTrack._split_joined_tags, faker.pydict())

    def test_from_tags(self, faker: Faker):
        sep = choice(LocalTrack._tag_sep)
        tags = {
            "title": ["Sleepwalk My Life Away"],
            "artist": ["Metallica"],
            "album": ["72 Seasons"],
            "album artist": ["Metallica"],
            "genre": ["Hard Rock", "Metal" + sep + "Rock", "Thrash Metal"],
            "track": ["04"],
            "disc": ["1/2"],
            "bpm": ["124.931"],
            "key": ["B"],
            "released_at": ["2023-04-14"],
            "comment": ["spotify:track:1WjgFpSxwA0Bqyr7hWc3f1"],
            "compilation": ["0"],
        }

        model = LocalTrack(**tags, path=faker.file_path())
        assert model.name == "Sleepwalk My Life Away"
        assert model.artist == "Metallica"
        assert model.album.name == "72 Seasons"
        assert [genre.name for genre in model.genres] == ["Hard Rock", "Metal", "Rock", "Thrash Metal"]
        assert model.track.number == 4
        assert model.track.total is None
        assert model.disc.number == 1
        assert model.disc.total == 2
        assert model.bpm == 124.931
        assert model.key.key == "B"
        assert model.released_at == date(2023, 4, 14)
        assert model.comments == tags["comment"]

    async def test_load(self, model: LocalTrack, faker: Faker):
        expected = LocalTrack(
            name=faker.sentence(),
            artists=faker.pylist(allowed_types=[str]),
            album=faker.word(),
            genres=faker.pylist(allowed_types=[str]),
            path=model.path,
        )

        with mock.patch.object(LocalTrack, "from_file", return_value=expected) as mocked_load:
            await model.load()

            mocked_load.assert_called_once_with(model.path)
            assert model is not expected
            assert model.name == expected.name
            assert model.artists == expected.artists
            assert model.album == expected.album
            assert model.genres == expected.genres
