from random import choice, sample

import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.item.genre import Genre, HasGenres
from tests.model.testers import MusifyResourceTester, UniqueKeyTester
from tests.utils import GENRES


class TestGenre(UniqueKeyTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return Genre(name=choice(GENRES))


class TestHasGenres(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return HasGenres(genres=[Genre(name=genre) for genre in sample(GENRES, k=faker.random_int(3, 6))])

    def test_from_string(self, faker: Faker):
        genres = sample(GENRES, k=faker.random_int(3, 6))
        model = HasGenres(genre=HasGenres._join_tags(genres))
        assert [genre.name for genre in model.genres] == genres
