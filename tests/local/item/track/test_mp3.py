from copy import deepcopy
from datetime import date
from io import BytesIO
from random import choice

import mutagen.id3
import pytest
from PIL import Image
from faker import Faker

from musify.local.item.track.mp3 import MP3
from musify.model import MusifyModel
from musify.model.properties.uri import URI
from tests.model.testers import UniqueKeyTester


class TestMP3(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return MP3(name=faker.sentence(), uri=uri, path=faker.file_path())

    @pytest.fixture
    def pictures(self, images: list[bytes]) -> list[mutagen.id3.APIC]:
        data = []
        for img in images:
            field = mutagen.id3.APIC()
            field.data = img
            data.append(field)

        return data
    
    @staticmethod
    def to_text_frame[T: mutagen.id3.TextFrame](value: str, cls: type[T] = mutagen.id3.TextFrame) -> T:
        obj = cls()
        obj.text = value
        return obj
    
    def test_merge_suffixed_tag_keys(self, faker: Faker):
        data: dict[str, str | bytes | list] = {
            "TIT2": "Track title",
            "TPE1": "Artist name",
            "TALB": "Album name",
            "APIC:Cover Front": faker.image(),
            "APIC:Cover Back": faker.image(),
            "COMM": faker.sentence(),
            "COMM:URI:eng": f"spotify:track:{"".join(faker.random_letters(19))}",
            "COMM:ID3V1 COMMENT:eng": faker.sentence(),
        }

        expected = deepcopy(data)
        expected["APIC"] = [expected.pop(key) for key in list(expected) if key.startswith("APIC")]
        expected["COMM"] = [expected.pop(key) for key in list(expected) if key.startswith("COMM")]

        # noinspection PyCallingNonCallable
        assert MP3._merge_suffixed_tag_keys(data) == expected

    def test_from_text_frame(self, faker: Faker):
        expected = faker.pystr()
        data = self.to_text_frame(expected)
        assert MP3._from_text_frame(data) == expected

    def test_from_text_frames(self, faker: Faker):
        expected = [faker.pystr() for _ in range(faker.random_int(3, 6))]
        data = [self.to_text_frame(item) for item in expected]
        assert MP3._from_text_frame(data) == expected

    def test_extract_images(self, images: list[bytes], pictures: list[mutagen.id3.APIC], faker: Faker):
        assert MP3._extract_images(None) is None
        assert MP3._extract_images(pictures[0]) == [images[0]]
        assert MP3._extract_images(pictures) == images

    def test_from_tags(self, images: list[bytes], pictures: list[mutagen.id3.APIC], faker: Faker):
        sep = choice(MP3._tag_sep)
        tags = {
            "TIT2": self.to_text_frame("Sleepwalk My Life Away", mutagen.id3.TIT2),
            "TPE1": self.to_text_frame("Metallica", mutagen.id3.TPE1),
            "TALB": self.to_text_frame("72 Seasons", mutagen.id3.TALB),
            "TPE2": self.to_text_frame("Metallica", mutagen.id3.TPE2),
            "TCON": self.to_text_frame(sep.join(("Hard Rock", "Metal", "Rock", "Thrash Metal")), mutagen.id3.TCON),
            "TRCK": self.to_text_frame("04", mutagen.id3.TRCK),
            "TPOS": self.to_text_frame("1/2", mutagen.id3.TPOS),
            "TBPM": self.to_text_frame("124.931", mutagen.id3.TBPM),
            "TKEY": self.to_text_frame("B", mutagen.id3.TKEY),
            choice(("TDRC", "TDAT", "TDOR", "TYER", "TORY")): self.to_text_frame(
                "2023-04-14", mutagen.id3.TDRC
            ),
            choice(("COMM", "COMMENT")) + ":ID3V1 COMMENT:eng": self.to_text_frame(
                faker.sentence(), mutagen.id3.COMM
            ),
            choice(("COMM", "COMMENT")) + ":URI:eng": self.to_text_frame(
                "spotify:track:1WjgFpSxwA0Bqyr7hWc3f1", mutagen.id3.COMM
            ),
            "APIC:Cover Front": pictures[0],
            "APIC:Cover Back": pictures[1],
            "APIC": pictures[2:],
        }

        model = MP3(**tags, path=faker.file_path())
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
        assert sorted(model.comments) == sorted(str(val) for key, val in tags.items() if key.startswith("COMM"))
        images = list(map(Image.open, map(BytesIO, images)))
        assert all(img in images for img in model.images)
