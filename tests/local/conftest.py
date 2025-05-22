from random import sample

import pytest
from faker import Faker

from musify.local.item.album import LocalAlbum
from musify.local.item.artist import LocalArtist
from musify.local.item.genre import LocalGenre
from musify.local.item.track import LocalTrack
from musify.model import MusifyResource
from musify.model.properties.uri import URI
from tests.utils import GENRES


@pytest.fixture
def models(
        tracks: list[LocalTrack],
        artists: list[LocalArtist],
        albums: list[LocalAlbum],
) -> list[MusifyResource]:
    return [*tracks, *artists, *albums]


@pytest.fixture
def tracks(faker: Faker) -> list[LocalTrack]:
    return [
        LocalTrack(name=faker.sentence(nb_words=faker.random_int(1, 5)), path=faker.file_path())
        for _ in range(faker.random_int(15, 30))
    ]


@pytest.fixture
def artists(faker: Faker) -> list[LocalArtist]:
    return [
        LocalArtist(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(5, 10))
    ]


@pytest.fixture
def albums(faker: Faker) -> list[LocalAlbum]:
    return [
        LocalAlbum(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(5, 10))
    ]


@pytest.fixture
def genres(faker: Faker) -> list[LocalGenre]:
    return [LocalGenre(name=genre) for genre in sample(GENRES, k=faker.random_int(3, 6))]
