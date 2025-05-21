import pytest
from faker import Faker

from musify.model import MusifyResource
from musify.model.collection.playlist import Playlist
from musify.model.item.album import Album
from musify.model.item.artist import Artist
from musify.model.item.track import Track


@pytest.fixture
def models(tracks: list[Track], artists: list[Artist], albums: list[Album]) -> list[MusifyResource]:
    return [*tracks, *artists, *albums]


@pytest.fixture
def tracks(faker: Faker) -> list[Track]:
    return [
        Track(name=faker.sentence(nb_words=faker.random_int(1, 5)))
        for _ in range(faker.random_int(5, 10))
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
def playlists(faker: Faker) -> list[Playlist]:
    return [Playlist(name=faker.sentence()) for _ in range(faker.random_int(10, 30))]
