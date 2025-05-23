from datetime import date

import pytest
from faker import Faker

from musify.local.item.track import LocalTrack
from musify.model import MusifyModel
from musify.model.properties.uri import URI
from tests.model.testers import UniqueKeyTester


class TestLocalTrack(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return LocalTrack(name=faker.sentence(), uri=uri, path=faker.file_path())

    def test_extract_first_value_from_single_sequence(self):
        assert LocalTrack._extract_first_value_from_single_sequence(None) is None
        assert LocalTrack._extract_first_value_from_single_sequence("Track name") == "Track name"
        assert LocalTrack._extract_first_value_from_single_sequence(["Track name"]) == "Track name"

        expected = ["Track name", "Artist name"]
        assert LocalTrack._extract_first_value_from_single_sequence(expected) == expected

    def test_convert_null_like_tag_values_to_null(self):
        assert LocalTrack._convert_null_like_tag_values_to_null(None) is None
        assert LocalTrack._convert_null_like_tag_values_to_null([]) is None
        assert LocalTrack._convert_null_like_tag_values_to_null(["", ""]) is None

        expected = ["12", 20]
        assert LocalTrack._convert_null_like_tag_values_to_null(expected) == expected

    def test_from_tags(self, faker: Faker):
        tags = {
            "title": ["Sleepwalk My Life Away"],
            "artist": ["Metallica"],
            "album": ["72 Seasons"],
            "album artist": ["Metallica"],
            "genre": ["Hard Rock", "Metal", "Old School Thrash", "Rock", "Thrash Metal"],
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
        assert [genre.name for genre in model.genres] == tags["genre"]
        assert model.track.number == 4
        assert model.track.total is None
        assert model.disc.number == 1
        assert model.disc.total == 2
        assert model.bpm == 124.931
        assert model.key.key == "B"
        assert model.released_at == date(2023, 4, 14)
        assert model.comments == ["spotify:track:1WjgFpSxwA0Bqyr7hWc3f1"]
