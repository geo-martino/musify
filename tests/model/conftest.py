import pytest
from faker import Faker

from musify.model import MusifyResource
from musify.model.item.album import Album
from musify.model.item.artist import Artist
from musify.model.item.track import Track


@pytest.fixture(scope="package")
def models(tracks: list[Track], artists: list[Artist], albums: list[Album]) -> list[MusifyResource]:
    return [*tracks, *artists, *albums]


@pytest.fixture(scope="package")
def tracks(faker: Faker) -> list[Track]:
    return [
        Track(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(1, 5))
    ]


@pytest.fixture(scope="package")
def artists(faker: Faker) -> list[Artist]:
    return [
        Artist(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(1, 5))
    ]


@pytest.fixture(scope="package")
def albums(faker: Faker) -> list[Album]:
    return [
        Album(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(1, 5))
    ]

