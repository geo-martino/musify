import re
from random import choice, sample
from typing import Any, Self

import pytest
from faker import Faker
from pydantic import model_validator
from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from yarl import URL

from musify.model import MusifyResource
from musify.model.collection.playlist import Playlist, MutablePlaylist
from musify.model.item.album import Album
from musify.model.item.artist import Artist
from musify.model.item.genre import Genre
from musify.model.item.track import Track
from tests.utils import GENRES


@pytest.fixture
def models(
        tracks: list[Track],
        artists: list[Artist],
        albums: list[Album],
        playlists: list[Playlist]
) -> list[MusifyResource]:
    return [*tracks, *artists, *albums, *playlists]


@pytest.fixture
def tracks(faker: Faker) -> list[Track]:
    return [
        Track(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(15, 30))
    ]


@pytest.fixture
def artists(faker: Faker) -> list[Artist]:
    return [
        Artist(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(5, 10))
    ]


@pytest.fixture
def albums(faker: Faker) -> list[Album]:
    return [
        Album(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(5, 10))
    ]


@pytest.fixture
def genres(faker: Faker) -> list[Genre]:
    return [Genre(name=genre) for genre in sample(GENRES, k=faker.random_int(3, 6))]


@pytest.fixture
def playlists(faker: Faker) -> list[Playlist]:
    return [MutablePlaylist(name=faker.sentence()) for _ in range(faker.random_int(10, 30))]
