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
from musify.model.properties.uri import URI
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
def genres(faker: Faker) -> list[Genre]:
    return [Genre(name=genre) for genre in sample(GENRES, k=faker.random_int(3, 6))]


@pytest.fixture
def playlists(faker: Faker) -> list[Playlist]:
    return [MutablePlaylist(name=faker.sentence()) for _ in range(faker.random_int(10, 30))]


class SimpleURI(URI):
    _source = None  # disable validation

    @property
    def source(self) -> str:
        return self.root.split(":")[0]

    @property
    def type(self) -> str:
        return self.root.split(":")[1]

    @property
    def id(self) -> str:
        return self.root.split(":")[2]

    @classmethod
    def from_id[T](cls, value: T, kind: str, source: str = None) -> T | Self:
        uri = ":".join((source or cls._source, kind, str(value)))
        return cls(uri)

    @property
    def href(self) -> URL:
        return URL.build(scheme="https", host="example.com", path=f"/api/{self.type}/{self.id}")

    @classmethod
    def from_href[T](cls, value: T, handler: ValidatorFunctionWrapHandler) -> T | Self:
        return cls.from_url(value, handler)

    @property
    def url(self) -> URL:
        return URL.build(scheme="https", host="example.com", path=f"/{self.type}/{self.id}")

    @classmethod
    def from_url[T](cls, value: T, handler: ValidatorFunctionWrapHandler) -> T | Self:
        if isinstance(value, str) and re.match(r"^https://example.com", value):
            value = URL(value)
        if not isinstance(value, URL):
            return value

        uri = ":".join((cls._source, *value.path.split("/")[:-2]))
        return handler(uri)


@pytest.fixture
def uri(models: list[MusifyResource], faker: Faker) -> SimpleURI:
    return SimpleURI.from_id(
        faker.random_int(int(10e9), int(10e10)), kind=choice(models).type, source=faker.word()
    )


@pytest.fixture
def uris(
    models: list[MusifyResource], faker: Faker
) -> list[SimpleURI]:
    seen = set()
    uris = []
    for model in models:
        source = None
        while source is None or source in seen:
            source = faker.word()

        uris.append(SimpleURI.from_id(faker.random_int(int(10e9), int(10e10)), kind=model.type, source=source))
        seen.add(source)

    return uris
