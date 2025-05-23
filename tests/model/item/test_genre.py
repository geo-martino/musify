from random import choice

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
    def model(self, genres: list[Genre]) -> MusifyModel:
        return HasGenres(genres=genres)

    def test_from_string(self, genres: list[Genre]):
        genre = HasGenres._join_tags(genre.name for genre in genres)
        model = HasGenres(genre=genre)
        assert [genre.name for genre in model.genres] == [genre.name for genre in genres]

    def test_to_string(self, genres: list[Genre]):
        genre = HasGenres._join_tags(genre.name for genre in genres)
        model = HasGenres(genre=genres)
        assert model.genre == genre
