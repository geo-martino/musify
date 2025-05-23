from datetime import date
from io import BytesIO
from pathlib import Path
from random import choice

from PIL import Image
# noinspection PyProtectedMember
from mutagen.asf import ASFUnicodeAttribute, ASFByteArrayAttribute
import pytest
from faker import Faker

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
            picture = ASFByteArrayAttribute()
            picture.value = img
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
        pictures = [choice([pic, pic.value]) for pic in pictures]
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

    async def test_load(self):
        path = Path("/Volumes/Media/Music/Little Shop of Horrors - 2003 Broadway Revival Cast/1-01 - Prologue - Little Shop of Horrors.wma")
        for field in await WMA.from_file(path=path):
            print(*field)
        raise

    async def test_load_old(self):
        from musify.libraries.local.track.wma import WMA
        path = Path("/Volumes/Media/Music/Little Shop of Horrors - 2003 Broadway Revival Cast/1-01 - Prologue - Little Shop of Horrors.wma")
        file = WMA(path)
        await file.load()
        raise
