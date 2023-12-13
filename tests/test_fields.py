import pytest

from syncify.abstract.collection import Playlist, Folder, Artist, Album
from syncify.abstract.item import Track, Artist as ArtistItem
from syncify.fields import FolderField, PlaylistField, AlbumField, ArtistField
from syncify.fields import TrackField, LocalTrackField, ArtistItemField
from syncify.local.track import LocalTrack

from tests.abstract.enums import FieldTester, TagFieldTester


class TestTrackField(TagFieldTester):

    @property
    def cls(self) -> type[TrackField]:
        return TrackField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return Track

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {TrackField.IMAGES}

    def test_map(self):
        assert self.cls.TRACK.to_tag() == {"track_number", "track_total"}
        assert self.cls.DISC.to_tag() == {"disc_number", "disc_total"}


class TestLocalTrackField(TagFieldTester):

    @property
    def cls(self) -> type[LocalTrackField]:
        return LocalTrackField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return LocalTrack

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {LocalTrackField.IMAGES}

    def test_map(self):
        assert self.cls.TRACK.to_tag() == {"track_number", "track_total"}
        assert self.cls.DISC.to_tag() == {"disc_number", "disc_total"}


class TestArtistItemField(TagFieldTester):

    @property
    def cls(self) -> type[ArtistItemField]:
        return ArtistItemField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return ArtistItem

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {ArtistItemField.IMAGES}


class TestPlaylistField(FieldTester):

    @property
    def cls(self) -> type[PlaylistField]:
        return PlaylistField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return Playlist

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {PlaylistField.IMAGES}


class TestFolderField(FieldTester):

    @property
    def cls(self) -> type[FolderField]:
        return FolderField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return Folder

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {FolderField.IMAGES}


class TestAlbumField(FieldTester):

    @property
    def cls(self) -> type[AlbumField]:
        return AlbumField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return Album

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {AlbumField.IMAGES}


class TestArtistField(FieldTester):

    @property
    def cls(self) -> type[ArtistField]:
        return ArtistField

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_cls():
        return Artist

    @staticmethod
    @pytest.fixture(scope="class")
    def reference_ignore():
        return {ArtistField.IMAGES}
