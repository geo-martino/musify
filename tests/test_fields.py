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

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return Track

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {TrackField.IMAGES}

    def test_map(self):
        assert self.cls.TRACK.to_tag() == {"track_number", "track_total"}
        assert self.cls.DISC.to_tag() == {"disc_number", "disc_total"}


class TestLocalTrackField(TagFieldTester):

    @property
    def cls(self) -> type[LocalTrackField]:
        return LocalTrackField

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return LocalTrack

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {LocalTrackField.IMAGES}

    def test_map(self):
        assert self.cls.TRACK.to_tag() == {"track_number", "track_total"}
        assert self.cls.DISC.to_tag() == {"disc_number", "disc_total"}


class TestArtistItemField(TagFieldTester):

    @property
    def cls(self) -> type[ArtistItemField]:
        return ArtistItemField

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return ArtistItem

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {ArtistItemField.IMAGES}


class TestPlaylistField(FieldTester):

    @property
    def cls(self) -> type[PlaylistField]:
        return PlaylistField

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return Playlist

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {PlaylistField.IMAGES}


class TestFolderField(FieldTester):

    @property
    def cls(self) -> type[FolderField]:
        return FolderField

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return Folder

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {FolderField.IMAGES}


class TestAlbumField(FieldTester):

    @property
    def cls(self) -> type[AlbumField]:
        return AlbumField

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return Album

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {AlbumField.IMAGES}


class TestArtistField(FieldTester):

    @property
    def cls(self) -> type[ArtistField]:
        return ArtistField

    @pytest.fixture(scope="class")
    def reference_cls(self):
        return Artist

    @pytest.fixture(scope="class")
    def reference_ignore(self):
        return {ArtistField.IMAGES}
