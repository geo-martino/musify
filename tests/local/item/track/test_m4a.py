from datetime import date
from io import BytesIO
from random import choice

import pytest
from PIL import Image
from faker import Faker
from mutagen.mp4 import MP4FreeForm, MP4Cover

from musify.local.item.track.m4a import M4A
from musify.model import MusifyModel
from musify.model.properties.uri import URI
from tests.model.testers import UniqueKeyTester


class TestM4A(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return M4A(name=faker.sentence(), uri=uri, path=faker.file_path())

    def test_from_free_form_field(self, faker: Faker):
        expected = faker.pystr()
        field = MP4FreeForm(expected.encode())

        assert M4A._from_free_form_field(field) == expected

    def test_from_free_form_fields(self, faker: Faker):
        expected = [faker.sentence() for _ in range(faker.random_int(3, 6))]
        attributes = [MP4FreeForm(item.encode()) for item in expected]

        assert M4A._from_free_form_fields(attributes) == expected

    def test_from_tags(self, images: list[bytes], faker: Faker):
        sep = choice(M4A._tag_sep)
        tags = {
            "©nam": ["Sleepwalk My Life Away"],
            "©ART": ["Metallica"],
            "©alb": ["72 Seasons"],
            "aART": ["Metallica"],
            choice(("----:com.apple.iTunes:GENRE", "©gen", "gnre")): [
                MP4FreeForm(b"Hard Rock"),
                MP4FreeForm(f"Metal{sep}Rock".encode()),
                MP4FreeForm(b"Thrash Metal")
            ],
            "trkn": [4],
            "disk": [(1, 2)],
            "tmpo": [124],
            "----:com.apple.iTunes:INITIALKEY": [MP4FreeForm(b"B")],
            "©day": ["2023-04-14"],
            "©cmt": ["spotify:track:1WjgFpSxwA0Bqyr7hWc3f1"],
            "covr": list(map(MP4Cover, images)),
            "cpil": True,
        }

        model = M4A.model_validate(tags | dict(path=faker.file_path()))

        assert model.name == "Sleepwalk My Life Away"
        assert model.artist == "Metallica"
        assert model.album.name == "72 Seasons"
        assert [genre.name for genre in model.genres] == ["Hard Rock", "Metal", "Rock", "Thrash Metal"]
        assert model.track.number == 4
        assert model.track.total is None
        assert model.disc.number == 1
        assert model.disc.total == 2
        assert model.bpm == 124
        assert model.key.key == "B"
        assert model.released_at == date(2023, 4, 14)
        assert model.comments == ["spotify:track:1WjgFpSxwA0Bqyr7hWc3f1"]
        assert model.images == list(map(Image.open, map(BytesIO, images)))
