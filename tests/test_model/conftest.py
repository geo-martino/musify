import pytest
from faker import Faker

from musify.model import MusifyResource
from musify.model.item.album import Album
from musify.model.item.artist import Artist
from musify.model.item.track import Track


@pytest.fixture(scope="package")
def models(faker: Faker) -> list[MusifyResource]:
    return [
        *(Track(name=faker.sentence(nb_words=faker.random_int(1, 5))) for _ in range(faker.random_int(1, 5))),
        *(Artist(name=faker.sentence(nb_words=faker.random_int(1, 5))) for _ in range(faker.random_int(1, 5))),
        *(Album(name=faker.sentence(nb_words=faker.random_int(1, 5))) for _ in range(faker.random_int(1, 5))),
    ]