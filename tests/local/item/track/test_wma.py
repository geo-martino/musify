import struct
from datetime import date
from io import BytesIO
from random import choice

import mutagen.id3
import pytest
from PIL import Image
from faker import Faker
# noinspection PyProtectedMember
from mutagen.asf import ASFUnicodeAttribute, ASFByteArrayAttribute

from musify.local.item.track.wma import WMA
from musify.model import MusifyModel
from musify.model.properties.uri import URI
from tests.model.testers import UniqueKeyTester


class TestWMA(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return WMA(name=faker.sentence(), uri=uri, path=faker.file_path())

    @pytest.fixture
    def pictures(self, images: list[bytes]) -> list[ASFByteArrayAttribute]:
        pictures = []
        for img in images:
            fmt = Image.open(BytesIO(img)).format

            header = struct.pack("<bi", mutagen.id3.PictureType.COVER_FRONT, len(img))
            header += Image.MIME[fmt].encode("utf-16") + b"\x00\x00"  # mime
            header += "".encode("utf-16") + b"\x00\x00"  # description

            picture = ASFByteArrayAttribute(header + img)
            pictures.append(picture)

        return pictures

    def test_from_unicode_attribute(self, faker: Faker):
        expected = faker.sentence()
        attribute = ASFUnicodeAttribute(expected)
        assert WMA._from_unicode_attribute(attribute) == expected

    def test_from_unicode_attributes(self, faker: Faker):
        expected = [faker.sentence() for _ in range(faker.random_int(3, 6))]
        attributes = [ASFUnicodeAttribute(item) for item in expected]
        assert WMA._from_unicode_attributes(attributes) == expected

    def test_extract_images(self, images: list[bytes], pictures: list[ASFByteArrayAttribute]):
        pictures = [choice([img, pic]) for img, pic in zip(images, pictures)]
        assert WMA._extract_images(pictures[0]) == [images[0]]
        assert WMA._extract_images(pictures) == images

    def test_from_tags(self, images: list[bytes], pictures: list[ASFByteArrayAttribute], faker: Faker):
        sep = choice(WMA._tag_sep)
        tags = {
            "Title": [ASFUnicodeAttribute("Sleepwalk My Life Away")],
            "Author": [ASFUnicodeAttribute("Metallica")],
            "WM/AlbumTitle": [ASFUnicodeAttribute("72 Seasons")],
            "WM/AlbumArtist": [ASFUnicodeAttribute("Metallica")],
            "WM/Genre": [
                ASFUnicodeAttribute("Hard Rock"),
                ASFUnicodeAttribute("Metal" + sep + "Rock"),
                ASFUnicodeAttribute("Thrash Metal")
            ],
            choice(("WM/TrackNumber", "TotalTracks")): [ASFUnicodeAttribute("04")],
            "WM/PartOfSet": [ASFUnicodeAttribute("1/2")],
            "WM/BeatsPerMinute": [ASFUnicodeAttribute("124.931")],
            "WM/InitialKey": [ASFUnicodeAttribute("B")],
            choice(("WM/Year", "WM/OriginalReleaseYear")): [ASFUnicodeAttribute("2023-04-14")],
            choice(("Description", "WM/Comments")): [ASFUnicodeAttribute("spotify:track:1WjgFpSxwA0Bqyr7hWc3f1")],
            "WM/Picture": pictures,
            "COMPILATION": [ASFUnicodeAttribute("0")],
        }

        model = WMA(**tags, path=faker.file_path())

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
