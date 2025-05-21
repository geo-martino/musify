from random import choice, sample

import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.item.album import Album
from musify.model.item.track import Track, HasTracks, HasMutableTracks
from musify.model.properties.order import Position
from musify.model.properties.uri import URI
from tests.model.testers import MusifyResourceTester, UniqueKeyTester


class TestTrack(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: URI, faker: Faker) -> MusifyModel:
        return Track(name=faker.sentence(), uri=uri)

    # noinspection PyUnresolvedReferences
    def test_set_track_total_from_album(self, faker: Faker):
        track = Track(name=faker.sentence(), album=Album(name=faker.sentence()))
        assert track.track is None, "Default value not replaced when no number found on Album"

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
        assert track.disc is None, "Default value not replaced when no number found on Album"

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
        assert track == track_equal, "Tracks should be equal"

        track_different_name = Track(name=faker.sentence(), artist=track.artist, album=track.album)
        assert track != track_different_name, "Tracks with different names should not be equal"

        track_different_artist = Track(name=track.name, artist=choice([None, faker.word()]), album=track.album)
        assert track != track_different_artist, "Tracks with different artists should not be equal"

        track_different_album = Track(name=track.name, artist=track.artist, album=choice([None, faker.word()]))
        assert track != track_different_album, "Tracks with different albums should not be equal"


class TestHasTracks(MusifyResourceTester):
    @pytest.fixture
    def model(self, tracks: list[Track]) -> MusifyModel:
        return HasTracks(tracks=tracks)

    def test_track_total(self, model: HasTracks):
        assert model.track_total == len(model.tracks), "Track total should be equal to the number of tracks"

    def test_disc_total(self, model: HasTracks, faker: Faker):
        for total in range(1, 6):
            for track in sample(model.tracks, 5):
                track.disc = Position(number=faker.random_int(1, total), total=total)

        assert model.disc_total == 5, "Disc total should be equal to the max number of discs in the tracks"

    def test_disc_total_skips_on_missing_value(self, model: HasTracks, faker: Faker):
        for track in model.tracks:
            track.disc = None

        assert model.disc_total is None


class TestHasMutableTracks(MusifyResourceTester):
    @pytest.fixture
    def model(self, tracks: list[Track]) -> MusifyModel:
        return HasMutableTracks(tracks=tracks)
