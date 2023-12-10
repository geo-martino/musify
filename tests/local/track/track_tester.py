from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname, splitext, getmtime

import pytest

from syncify.abstract.item import Item
from syncify.fields import LocalTrackField
from syncify.local.exception import InvalidFileType
from syncify.local.file import open_image
from syncify.local.track import LocalTrack, load_track
from tests import path_resources, path_txt
from tests.abstract.item import ItemTester
from tests.local import remote_wrangler
from tests.local.track import path_track_all, path_track_img
from tests.remote import random_uri


def test_does_not_load_invalid_track():
    # raises error on unrecognised file type
    with pytest.raises(InvalidFileType):
        load_track(path_txt)


class LocalTrackTester(ItemTester, metaclass=ABCMeta):

    @property
    @abstractmethod
    def track_class(self) -> type[LocalTrack]:
        """The class of :py:class:`LocalTrack` implementation to be tested."""
        raise NotImplementedError

    @property
    @abstractmethod
    def track_count(self) -> int:
        """Count of all available tracks of this type in the resources folder"""
        raise NotImplementedError

    def load_track(self, path: str) -> LocalTrack:
        """Load the track object from a given path"""
        return self.track_class(file=path, available=path_track_all, remote_wrangler=remote_wrangler)

    @abstractmethod
    def track(self, path: str) -> LocalTrack:
        """Yields a :py:class:`LocalTrack` object from a given path as pytest.fixture"""
        raise NotImplementedError

    @staticmethod
    @pytest.fixture
    def item(track: LocalTrack) -> Item:
        return track

    def test_does_not_load_other_supported_track_types(self):
        # noinspection PyTypeChecker
        paths = [
            path for path in path_track_all
            if not all(path.casefold().endswith(ext) for ext in self.track_class.valid_extensions)
        ]
        with pytest.raises(InvalidFileType):
            for path in paths:
                self.load_track(path)

    def test_load_track_function(self, track: LocalTrack):
        track = load_track(track.path)
        assert track.__class__ == self.track_class
        assert track.path == track.path

    def test_load_track_class(self, track: LocalTrack):
        track_file = track.file

        track._file = track.get_file()
        track_reload_1 = track.file

        track.load()
        track_reload_2 = track.file

        # has actually reloaded the file in each reload
        assert id(track_file) != id(track_reload_1) != id(track_reload_2)

        # raises error on unrecognised file type
        with pytest.raises(InvalidFileType):
            self.track_class(file=path_txt, available=path_track_all)

        # raises error on files that do not exist
        with pytest.raises(FileNotFoundError):
            self.track_class(file=f"does_not_exist.{set(track.valid_extensions).pop()}", available=path_track_all)

    def test_copy_track(self, track: LocalTrack):
        track_from_file = self.track_class(file=track.file, available=path_track_all)
        assert id(track.file) == id(track_from_file.file)

        track_copy = copy(track)
        assert id(track.file) == id(track_copy.file)
        for key, value in vars(track).items():
            assert value == track_copy[key]

        track_deepcopy = deepcopy(track)
        assert id(track.file) != id(track_deepcopy.file)
        for key, value in vars(track).items():
            assert value == track_deepcopy[key]

    def test_set_and_find_file_paths(self, track: LocalTrack, tmp_path: str):
        paths = self.track_class.get_filepaths(tmp_path)
        assert paths == {track.path}
        assert len(self.track_class.get_filepaths(path_resources)) == self.track_count

        assert self.track_class(file=track.path.upper(), available=paths).path == track.path

    def test_clear_tags_dry_run(self, track: LocalTrack):
        track_update = track
        track_original = copy(track)

        # when dry run, no updates should happen
        result = track_update.delete_tags(tags=LocalTrackField.ALL, dry_run=True)
        assert not result.saved

        track_update_dry = self.load_track(track.path)

        assert track_update_dry.title == track_original.title
        assert track_update_dry.artist == track_original.artist
        assert track_update_dry.album == track_original.album
        assert track_update_dry.album_artist == track_original.album_artist
        assert track_update_dry.track_number == track_original.track_number
        assert track_update_dry.track_total == track_original.track_total
        assert track_update_dry.genres == track_original.genres
        assert track_update_dry.year == track_original.year
        assert track_update_dry.bpm == track_original.bpm
        assert track_update_dry.key == track_original.key
        assert track_update_dry.disc_number == track_original.disc_number
        assert track_update_dry.disc_total == track_original.disc_total
        assert track_update_dry.compilation == track_original.compilation
        assert track_update_dry.comments == track_original.comments

        assert track_update_dry.uri == track_original.uri
        assert track_update_dry.has_uri == track_original.has_uri
        assert track_update_dry.has_image == track_original.has_image

    def test_clear_tags(self, track: LocalTrack):
        track_update = track
        track_original = copy(track)

        result = track_update.delete_tags(tags=LocalTrackField.ALL, dry_run=False)
        assert result.saved

        track_update = self.load_track(track.path)

        assert track_update.title is None
        assert track_update.artist is None
        assert track_update.album is None
        assert track_update.album_artist is None
        assert track_update.track_number is None
        assert track_update.track_total is None
        assert track_update.genres is None
        assert track_update.year is None
        assert track_update.bpm is None
        assert track_update.key is None
        assert track_update.disc_number is None
        assert track_update.disc_total is None
        assert not track_update.compilation
        assert track_update.comments is None

        assert track_update.uri is None
        assert track.has_uri == track_original.has_uri
        assert not track_update.has_image

    @staticmethod
    def get_update_tags_test_track(track: LocalTrack) -> tuple[LocalTrack, LocalTrack, str]:
        """Load track and modify its tags for update tags tests"""
        track_original = copy(track)
        new_uri = remote_wrangler.unavailable_uri_dummy if track.has_uri else random_uri()

        track.title = "new title"
        track.artist = "new artist"
        track.album = "new album artist"
        track.album_artist = "new various"
        track.track_number = 2
        track.track_total = 3
        track.genres = ["Big Band", "Swing"]
        track.year = 1956
        track.bpm = 98.0
        track.key = "F#"
        track.disc_number = 2
        track.disc_total = 3
        track.compilation = False
        track.uri = new_uri
        track.image_links.clear()

        return track, track_original, new_uri

    def test_update_tags_dry_run(self, track: LocalTrack):
        track_update, track_original, _ = self.get_update_tags_test_track(track)

        # dry run, no updates should happen
        result = track_update.save(tags=LocalTrackField.ALL, replace=False, dry_run=True)
        assert not result.saved

        track_update_dry = deepcopy(track_update)

        assert track_update_dry.title == track_original.title
        assert track_update_dry.artist == track_original.artist
        assert track_update_dry.album == track_original.album
        assert track_update_dry.album_artist == track_original.album_artist
        assert track_update_dry.track_number == track_original.track_number
        assert track_update_dry.track_total == track_original.track_total
        assert track_update_dry.genres == track_original.genres
        assert track_update_dry.year == track_original.year
        assert track_update_dry.bpm == track_original.bpm
        assert track_update_dry.key == track_original.key
        assert track_update_dry.disc_number == track_original.disc_number
        assert track_update_dry.disc_total == track_original.disc_total
        assert track_update_dry.compilation == track_original.compilation
        assert track_update_dry.comments == track_original.comments

        assert track_update_dry.uri == track_original.uri
        assert track_update_dry.has_uri == track_original.has_uri
        assert track_update_dry.has_image == track_original.has_image

    def test_update_tags_no_replace(self, track: LocalTrack):
        track_update, track_original, new_uri = self.get_update_tags_test_track(track)

        # update and don't replace current tags (except URI if URI is False)
        result = track_update.save(tags=LocalTrackField.ALL, replace=False, dry_run=False)
        assert result.saved

        track_update = deepcopy(track_update)

        assert track_update.title == track_original.title
        assert track_update.artist == track_original.artist
        assert track_update.album == track_original.album
        assert track_update.album_artist == track_original.album_artist
        assert track_update.track_number == track_original.track_number
        assert track_update.track_total == track_original.track_total
        assert track_update.genres == track_original.genres
        assert track_update.year == track_original.year
        assert track_update.bpm == track_original.bpm
        assert track_update.key == track_original.key
        assert track_update.disc_number == track_original.disc_number
        assert track_update.disc_total == track_original.disc_total
        assert track_update.compilation == track_original.compilation
        assert track_update.comments == [new_uri]

        if new_uri == remote_wrangler.unavailable_uri_dummy:
            assert track_update.uri is None
        else:
            assert track_update.uri == new_uri
        assert track_update.has_uri == track_update.has_uri
        assert track_update.has_image == track_original.has_image

    def test_update_tags_with_replace(self, track: LocalTrack):
        track_update, track_original, new_uri = self.get_update_tags_test_track(track)

        result = track_update.save(tags=LocalTrackField.ALL, replace=True, dry_run=False)
        assert result.saved
        track_update_replace = deepcopy(track_update)

        assert track_update_replace.title == track_update.title
        assert track_update_replace.artist == track_update.artist
        assert track_update_replace.album == track_update.album
        assert track_update_replace.album_artist == track_update.album_artist
        assert track_update_replace.track_number == track_update.track_number
        assert track_update_replace.track_total == track_update.track_total
        assert track_update_replace.genres == track_update.genres
        assert track_update_replace.year == track_update.year
        assert track_update_replace.bpm == track_update.bpm
        assert track_update_replace.key == track_update.key
        assert track_update_replace.disc_number == track_update.disc_number
        assert track_update_replace.disc_total == track_update.disc_total
        assert track_update_replace.compilation == track_update.compilation
        assert track_update_replace.comments == [new_uri]

        if new_uri == remote_wrangler.unavailable_uri_dummy:
            assert track_update.uri is None
        else:
            assert track_update.uri == new_uri
        assert track_update_replace.image_links == track_update.image_links
        assert track_update_replace.has_image == track_update.has_image

    # noinspection PyProtectedMember
    @staticmethod
    def get_update_image_test_track(track: LocalTrack) -> tuple[LocalTrack, LocalTrack]:
        """Load track and modify its tags for update tags tests"""
        track._image_links = {"cover_front": path_track_img}
        return track, copy(track)

    # noinspection PyProtectedMember
    def test_update_image_dry_run(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        image_original = track_update._read_images()[0]

        # dry run, no updates should happen
        result = track_update.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=True)
        assert not result.saved

        track_update_dry = deepcopy(track_update)
        image_update_dry = track_update_dry._read_images()[0]
        assert track_update_dry.has_image == track_original.has_image
        assert image_update_dry.size == image_original.size

    def test_update_image_no_replace(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        # clear current image and update
        track_update.delete_tags(LocalTrackField.IMAGES, dry_run=False)
        assert not track_update.has_image

        result = track_update.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=False)
        assert result.saved

        track_update = deepcopy(track_update)
        image_update = track_update._read_images()[0]
        assert track_update.has_image
        assert image_update.size == open_image(path_track_img).size

    def test_update_image_with_replace(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        result = track_update.save(tags=LocalTrackField.IMAGES, replace=True, dry_run=False)
        assert result.saved

        track_update_replace = deepcopy(track_update)
        image_update_replace = track_update_replace._read_images()[0]
        assert track_update_replace.has_image
        assert image_update_replace.size == open_image(path_track_img).size

    @staticmethod
    def test_loaded_attributes_common(track: LocalTrack):
        assert track.image_links == {}
        assert track.has_image

        # file properties
        assert track.folder == basename(dirname(track.path))
        assert track.filename == splitext(basename(track.path))[0]
        assert track.kind == track.__class__.__name__
        assert track.date_modified == datetime.fromtimestamp(getmtime(track.path))

        # library properties
        assert track.rating is None
        assert track.date_added is None
        assert track.last_played is None
        assert track.play_count is None
