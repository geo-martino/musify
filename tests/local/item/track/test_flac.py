from datetime import date
from io import BytesIO
from pathlib import Path
from random import choice

import mutagen.flac
import pytest
from PIL import Image
from faker import Faker

from musify.local.item.track.flac import FLAC
from musify.model import MusifyModel
from musify.model.properties.uri import URI
from tests.model.testers import UniqueKeyTester


class TestFLAC(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return FLAC(name=faker.sentence(), uri=uri, path=faker.file_path())

    @pytest.fixture
    def pictures(self, images: list[bytes]) -> list[mutagen.flac.Picture]:
        pictures = []
        for img in images:
            picture = mutagen.flac.Picture()
            picture.data = img
            pictures.append(picture)

        return pictures

    @pytest.fixture
    def file(self, pictures: list[mutagen.flac.Picture], faker: Faker, tmp_path: Path) -> mutagen.flac.FLAC:
        path = tmp_path.joinpath(faker.file_name(category="audio"))

        file = mutagen.flac.FLAC()
        file.filename = str(path)
        file.tags = {"name": "Track title"}
        file.metadata_blocks = [p for p in pictures]

        return file

    # noinspection PyCallingNonCallable
    def test_from_mutagen(self, file: mutagen.flac.FLAC, faker: Faker):
        tags = faker.pydict()
        file.tags = tags
        assert file.filename
        assert file.pictures

        assert FLAC._from_mutagen(tags) is tags
        assert FLAC._from_mutagen(file.filename) is file.filename

        result = FLAC._from_mutagen(file)
        assert result == tags | dict(images=file.pictures, path=file.filename)

    # noinspection PyCallingNonCallable
    def test_merge_position_values(self):
        tags = {
            "title": ["Sleepwalk My Life Away"],
            "artist": ["Metallica"],
            "album": ["72 Seasons"],
            "album artist": ["Metallica"],
            "track": 3,
            "tracknumber": 5,
            "tracktotal": 10,
            "discnumber": 2,
            "disctotal": 5,
        }
        result = FLAC._merge_position_values(tags)

        assert sum(key.startswith("track") for key in result) == 1
        assert result["tracknumber"] == (3, 10)

        assert sum(key.startswith("disc") for key in result) == 1
        assert result["discnumber"] == (2, 5)

    def test_extract_images(self, images: list[bytes], pictures: list[mutagen.flac.Picture]):
        pictures = [choice([pic, pic.data]) for pic in pictures]
        assert FLAC._extract_images(pictures[0]) == [images[0]]
        assert FLAC._extract_images(pictures) == images

    def test_from_tags(self, images: list[bytes], pictures: list[mutagen.flac.Picture], faker: Faker):
        sep = choice(FLAC._tag_sep)
        tags = {
            "title": ["Sleepwalk My Life Away"],
            "artist": ["Metallica"],
            "album": ["72 Seasons"],
            "album artist": ["Metallica"],
            "genre": ["Hard Rock", "Metal" + sep + "Rock", "Thrash Metal"],
            choice(("tracknumber", "tracktotal")): ["04"],
            "discnumber": ["1"],
            "disctotal": ["2"],
            "bpm": ["124.931"],
            "key": ["B"],
            choice(("date", "year")): ["2023-04-14"],
            choice(("comment", "description")): ["spotify:track:1WjgFpSxwA0Bqyr7hWc3f1"],
            "compilation": ["0"],
            "images": pictures,
        }

        model = FLAC(**tags, path=faker.file_path())
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
        assert model.comments == ["spotify:track:1WjgFpSxwA0Bqyr7hWc3f1"]
        assert model.images == list(map(Image.open, map(BytesIO, images)))
