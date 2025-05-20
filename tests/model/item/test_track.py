from random import choice

import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.item.album import Album
from musify.model.item.track import Track
from tests.model.testers import MusifyResourceTester


class TestTrack(MusifyResourceTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return Track(name=faker.sentence())

    # noinspection PyUnresolvedReferences
    def test_set_track_total_from_album(self, faker: Faker):
        track = Track(name=faker.sentence(), album=Album(name=faker.sentence()))
        assert track.track is None, "Default value replaced when no number found on Album"

        album = Album(name=faker.sentence(), track_total=faker.random_int(10, 20))

        track = Track(name=faker.sentence(), album=album)
        assert track.track.number is None
        assert track.track.total == album.track_total

        track = Track(name=faker.sentence(), album=album, track=5)
        assert track.track.number == 5
        assert track.track.total == album.track_total

    # noinspection PyUnresolvedReferences
    def test_set_disc_total_from_album(self, faker: Faker):
        track = Track(name=faker.sentence(), album=Album(name=faker.sentence()))
        assert track.disc is None, "Default value replaced when no number found on Album"

        album = Album(name=faker.sentence(), disc_total=faker.random_int(10, 20))

        track = Track(name=faker.sentence(), album=album)
        assert track.disc.number is None
        assert track.disc.total == album.disc_total

        track = Track(name=faker.sentence(), album=album, disc=5)
        assert track.disc.number == 5
        assert track.disc.total == album.disc_total

    def test_equality(self, faker: Faker):
        track = Track(name=faker.sentence(), artist=faker.word(), album=faker.word())
        track_equal = Track(name=track.name, artist=track.artist, album=track.album)
        assert track != track_equal, "Tracks should be equal"

        track_different_name = Track(name=faker.sentence(), artist=track.artist, album=track.album)
        assert track != track_different_name, "Tracks with different names should not be equal"

        track_different_artist = Track(name=track.name, artist=choice([None, faker.word()]), album=track.album)
        assert track != track_different_artist, "Tracks with different artists should not be equal"

        track_different_album = Track(name=track.name, artist=track.artist, album=choice([None, faker.word()]))
        assert track != track_different_album, "Tracks with different albums should not be equal"

