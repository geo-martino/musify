import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.item.artist import Artist, HasArtists
from tests.model.testers import MusifyResourceTester


class TestArtist(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return Artist(name=faker.word())

    def test_from_string(self, faker: Faker):
        artists = [faker.word() for _ in range(faker.random_int(3, 6))]
        model = HasArtists(artist=HasArtists._join_tags(artists))
        assert [artist.name for artist in model.artists] == artists
