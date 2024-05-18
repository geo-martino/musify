from copy import copy, deepcopy
from datetime import datetime, date
from os.path import basename, dirname, splitext, getmtime
from pathlib import Path

import pytest
from PIL.Image import Image

from musify.core.base import MusifyItem
from musify.exception import MusifyKeyError
from musify.file.exception import InvalidFileType, FileDoesNotExistError
from musify.file.image import open_image
from musify.libraries.core.object import Track
from musify.libraries.local.track import LocalTrack, load_track, FLAC, M4A, MP3, WMA, SyncResultTrack
from musify.libraries.local.track.field import LocalTrackField
from musify.libraries.remote.core.enum import RemoteObjectType
from tests.core.base import MusifyItemTester
from tests.libraries.local.utils import path_track_all, path_track_img, path_track_resources
from tests.libraries.remote.spotify.utils import random_uri
from tests.utils import path_txt


def test_does_not_load_invalid_track():
    # raises error on unrecognised file type
    with pytest.raises(InvalidFileType):
        load_track(path_txt)


def test_loaded_attributes_flac(track_flac: FLAC):
    assert track_flac.tag_sep == "; "

    # metadata
    assert track_flac.title == "title 1"
    assert track_flac.artist == "artist 1"
    assert track_flac.artists == ["artist 1"]
    assert track_flac.album == "album artist 1"
    assert track_flac.album_artist == "various"
    assert track_flac.track_number == 1
    assert track_flac.track_total == 4
    assert track_flac.genres == ["Pop", "Rock", "Jazz"]
    assert track_flac.date == date(2020, 3, 25)
    assert track_flac.year == 2020
    assert track_flac.month == 3
    assert track_flac.day == 25
    assert track_flac.bpm == 120.12
    assert track_flac.key == 'A'
    assert track_flac.disc_number == 1
    assert track_flac.disc_total == 3
    assert track_flac.compilation
    # noinspection SpellCheckingInspection
    assert track_flac.comments == ["spotify:track:6fWoFduMpBem73DMLCOh1Z"]

    assert track_flac.uri == track_flac.comments[0]
    assert track_flac.has_uri

    # file properties
    assert int(track_flac.length) == 20
    # assert track.path == path_track_flac  # uses tmp_path instead
    assert track_flac.ext == ".flac"
    assert track_flac.size == 1818191
    assert track_flac.channels == 1
    assert track_flac.bit_rate == 706.413
    assert track_flac.bit_depth == 16
    assert track_flac.sample_rate == 44.1


def test_loaded_attributes_mp3(track_mp3: MP3):
    assert track_mp3.tag_sep == "; "

    # metadata
    assert track_mp3.title == "title 2"
    assert track_mp3.artist == "artist 2; another artist"
    assert track_mp3.artists == ["artist 2", "another artist"]
    assert track_mp3.album == "album artist 2"
    assert track_mp3.album_artist == "various"
    assert track_mp3.track_number == 3
    assert track_mp3.track_total == 4
    assert track_mp3.genres == ["Pop Rock", "Musical"]
    assert track_mp3.date == date(2024, 5, 1)
    assert track_mp3.year == 2024
    assert track_mp3.month == 5
    assert track_mp3.day == 1
    assert track_mp3.bpm == 200.56
    assert track_mp3.key == 'C'
    assert track_mp3.disc_number == 2
    assert track_mp3.disc_total == 3
    assert not track_mp3.compilation
    # noinspection SpellCheckingInspection
    assert track_mp3.comments == ["spotify:track:1TjVbzJUAuOvas1bL00TiH"]

    assert track_mp3.uri == track_mp3.comments[0]
    assert track_mp3.has_uri

    # file properties
    assert int(track_mp3.length) == 30
    # assert track.path == path_track_mp3  # uses tmp_path instead
    assert track_mp3.ext == ".mp3"
    assert track_mp3.size == 410910
    assert track_mp3.channels == 1
    assert track_mp3.bit_rate == 96.0
    assert track_mp3.bit_depth is None
    assert track_mp3.sample_rate == 44.1


def test_loaded_attributes_m4a(track_m4a: M4A):
    assert track_m4a.tag_sep == "; "

    # metadata
    assert track_m4a.title == "title 3"
    assert track_m4a.artist == "artist 3"
    assert track_m4a.artists == ["artist 3"]
    assert track_m4a.album == "album artist 3"
    assert track_m4a.album_artist == "various"
    assert track_m4a.track_number == 2
    assert track_m4a.track_total == 4
    assert track_m4a.genres == ["Dance", "Techno"]
    assert track_m4a.date is None
    assert track_m4a.year == 2021
    assert track_m4a.month == 12
    assert track_m4a.day is None
    assert track_m4a.bpm == 120.0
    assert track_m4a.key == 'B'
    assert track_m4a.disc_number == 1
    assert track_m4a.disc_total == 2
    assert track_m4a.compilation
    assert track_m4a.comments == ["spotify:track:4npv0xZO9fVLBmDS2XP9Bw"]

    assert track_m4a.uri == track_m4a.comments[0]
    assert track_m4a.has_uri

    # file properties
    assert int(track_m4a.length) == 20
    # assert track.path == path_track_m4a  # uses tmp_path instead
    assert track_m4a.ext == ".m4a"
    assert track_m4a.size == 302199
    assert track_m4a.channels == 2
    assert track_m4a.bit_rate == 98.17
    assert track_m4a.bit_depth == 16
    assert track_m4a.sample_rate == 44.1


def test_loaded_attributes_wma(track_wma: WMA):
    assert track_wma.tag_sep == "; "

    # metadata
    assert track_wma.title == "title 4"
    assert track_wma.artist == "artist 4"
    assert track_wma.artists == ["artist 4"]
    assert track_wma.album == "album artist 4"
    assert track_wma.album_artist == "various"
    assert track_wma.track_number == 4
    assert track_wma.track_total == 4
    assert track_wma.genres == ["Metal", "Rock"]
    assert track_wma.date is None
    assert track_wma.year == 2023
    assert track_wma.month is None
    assert track_wma.day is None
    assert track_wma.bpm == 200.56
    assert track_wma.key == 'D'
    assert track_wma.disc_number == 3
    assert track_wma.disc_total == 4
    assert not track_wma.compilation
    assert track_wma.comments == [track_wma._reader.unavailable_uri_dummy]

    assert track_wma.uri is None
    assert not track_wma.has_uri

    # file properties
    assert int(track_wma.length) == 32
    # assert track.path == path_track_wma  # uses tmp_path instead
    assert track_wma.ext == ".wma"
    assert track_wma.size == 1193637
    assert track_wma.channels == 1
    assert track_wma.bit_rate == 96.0
    assert track_wma.bit_depth is None
    assert track_wma.sample_rate == 44.1


def test_loaded_attributes_common(track: LocalTrack):
    assert track.image_links == {}
    assert track.has_image

    # file properties
    assert track.folder == basename(dirname(track.path))
    assert track.filename == splitext(basename(track.path))[0]
    assert track.type == track.__class__.__name__
    assert track.date_modified == datetime.fromtimestamp(getmtime(track.path))

    # library properties
    assert track.rating is None
    assert track.date_added is None
    assert track.last_played is None
    assert track.play_count is None


class TestLocalTrack(MusifyItemTester):
    """Run generic tests for :py:class:`LocalTrack` implementations"""

    @pytest.fixture
    def item(self, track: LocalTrack) -> MusifyItem:
        return track

    @pytest.fixture
    def item_unequal(self, track: LocalTrack) -> LocalTrack:
        return next(load_track(path) for path in path_track_all if path != track.path)

    @pytest.fixture
    def item_modified(self, track: LocalTrack) -> MusifyItem:
        track = copy(track)
        track.title = "new title"
        track.artist = "new artist"
        track.uri = random_uri(kind=RemoteObjectType.TRACK)
        return track

    def test_does_not_load_other_supported_track_types(self, track: LocalTrack):
        paths = [
            path for path in path_track_all
            if not all(path.casefold().endswith(ext) for ext in track.valid_extensions)
        ]
        with pytest.raises(InvalidFileType):
            for path in paths:
                track.__class__(path)

    def test_load_track_function(self, track: LocalTrack):
        track_reload = load_track(track.path)
        assert track_reload.__class__ == track.__class__
        assert track_reload.path == track.path

    def test_load_track_class(self, track: LocalTrack):
        # has actually reloaded the file
        assert id(track._reader.file) != id(track.load())

        # raises error on unrecognised file type
        with pytest.raises(InvalidFileType):
            track.__class__(file=path_txt)

        # raises error on files that do not exist
        with pytest.raises(FileDoesNotExistError):
            track.__class__(file=f"does_not_exist.{set(track.valid_extensions).pop()}")

    def test_copy_track(self, track: LocalTrack):
        track_from_file = track.__class__(file=track._reader.file)
        assert id(track._reader.file) == id(track_from_file._reader.file)

        keys = [key for key in track.__slots__ if key.lstrip("_") in dir(track)]

        track_copy = copy(track)
        assert id(track._reader.file) == id(track_copy._reader.file)
        for key in keys:
            assert getattr(track, key) == getattr(track_copy, key)

        track_deepcopy = deepcopy(track)
        assert id(track._reader.file) != id(track_deepcopy._reader.file)
        for key in keys:
            assert getattr(track, key) == getattr(track_deepcopy, key)

    def test_set_and_find_file_paths(self, track: LocalTrack, tmp_path: Path):
        paths = track.__class__.get_filepaths(str(tmp_path))
        assert paths == {track.path}
        assert len(track.__class__.get_filepaths(path_track_resources)) == 1

    def test_setitem_dunder_method(self, track: LocalTrack):
        assert track.uri != "new_uri"
        track["uri"] = "new_uri"
        assert track.uri == "new_uri"

        with pytest.raises(MusifyKeyError):
            track["bad key"] = "value"

        with pytest.raises(AttributeError):
            track["name"] = "cannot set name"

    def test_merge(self, track: LocalTrack, item_modified: Track):
        assert track.title != item_modified.title
        assert track.artist != item_modified.artist
        assert track.uri != item_modified.uri
        assert track.album == item_modified.album
        assert track.rating == item_modified.rating

        track.merge(item_modified, tags={LocalTrackField.TITLE, LocalTrackField.URI})
        assert track.title == item_modified.title
        assert track.artist != item_modified.artist
        assert track.uri == item_modified.uri
        assert track.album == item_modified.album
        assert track.rating == item_modified.rating

    def test_merge_dunder_methods(self, track: LocalTrack, item_modified: Track):
        assert track.title != item_modified.title
        assert track.artist != item_modified.artist
        assert track.uri != item_modified.uri
        assert track.album == item_modified.album
        assert track.rating == item_modified.rating

        new_track = track | item_modified
        assert track.title != item_modified.title
        assert track.artist != item_modified.artist
        assert track.uri != item_modified.uri

        assert new_track.title == item_modified.title
        assert new_track.artist == item_modified.artist
        assert new_track.uri == item_modified.uri
        assert new_track.album == item_modified.album
        assert new_track.rating == item_modified.rating

        track |= item_modified
        assert track.title == item_modified.title
        assert track.artist == item_modified.artist
        assert track.uri == item_modified.uri
        assert track.album == item_modified.album
        assert track.rating == item_modified.rating


class TestLocalTrackWriter:

    @staticmethod
    def assert_track_tags_equal(actual: LocalTrack, expected: LocalTrack):
        """Assert the tags of the givens tracks equal."""
        assert actual.title == expected.title, "title"
        assert actual.artist == expected.artist, "artist"
        assert actual.album == expected.album, "album"
        assert actual.album_artist == expected.album_artist, "album_artist"
        assert actual.track_number == expected.track_number, "track_number"
        assert actual.track_total == expected.track_total, "track_total"
        assert actual.genres == expected.genres, "genres"
        assert actual.date == expected.date, "date"
        assert actual.year == expected.year, "year"
        assert actual.month == expected.month, "month"
        assert actual.day == expected.day, "day"
        assert actual.bpm == expected.bpm, "bpm"
        assert actual.key == expected.key, "key"
        assert actual.disc_number == expected.disc_number, "disc_number"
        assert actual.disc_total == expected.disc_total, "disc_total"
        assert actual.compilation == expected.compilation, "compilation"

    @staticmethod
    def assert_track_tags_equal_on_existing(actual: LocalTrack, expected: LocalTrack):
        """Assert the tags of the givens tracks equal only when a mapping for that tag exists."""
        assert not actual.tag_map.title or actual.title == expected.title, "title"
        assert not actual.tag_map.artist or actual.artist == expected.artist, "artist"
        assert not actual.tag_map.album or actual.album == expected.album, "album"
        assert not actual.tag_map.album_artist or actual.album_artist == expected.album_artist, "album_artist"
        assert not actual.tag_map.track_number or actual.track_number == expected.track_number, "track_number"
        assert not actual.tag_map.track_total or actual.track_total == expected.track_total, "track_total"
        assert not actual.tag_map.genres or actual.genres == expected.genres, "genres"
        assert not actual.tag_map.date or actual.date == expected.date, "date"
        assert not actual.tag_map.year or actual.year == expected.year, "year"
        assert not actual.tag_map.month or actual.month == expected.month, "month"
        assert not actual.tag_map.day or actual.day == expected.day, "day"
        assert not actual.tag_map.bpm or actual.bpm == expected.bpm, "bpm"
        assert not actual.tag_map.key or actual.key == expected.key, "key"
        assert not actual.tag_map.disc_number or actual.disc_number == expected.disc_number, "disc_number"
        assert not actual.tag_map.disc_total or actual.disc_total == expected.disc_total, "disc_total"
        assert not actual.tag_map.compilation or actual.compilation == expected.compilation, "compilation"

    def test_clear_tags_dry_run(self, track: LocalTrack):
        track_update = track
        track_original = copy(track)

        # when dry run, no updates should happen
        result = track_update.delete_tags(tags=LocalTrackField.ALL, dry_run=True)
        assert not result.saved

        # noinspection PyTestUnpassedFixture
        track_update_dry = load_track(track.path, remote_wrangler=track._reader.remote_wrangler)

        self.assert_track_tags_equal(track_update_dry, track_original)
        assert track_update.comments == track_original.comments

        assert track_update_dry.uri == track_original.uri
        assert track_update_dry.has_uri == track_original.has_uri
        assert track_update_dry.has_image == track_original.has_image

    def test_clear_tags(self, track: LocalTrack):
        track_update = track
        track_original = copy(track)

        result = track_update.delete_tags(tags=LocalTrackField.ALL, dry_run=False)
        assert result.saved

        # noinspection PyTestUnpassedFixture
        track_update = load_track(track.path, remote_wrangler=track._reader.remote_wrangler)

        assert track_update.title is None
        assert track_update.artist is None
        assert track_update.album is None
        assert track_update.album_artist is None
        assert track_update.track_number is None
        assert track_update.track_total is None
        assert track_update.genres is None
        assert track_update.date is None
        assert track_update.year is None
        assert track_update.month is None
        assert track_update.day is None
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
        new_uri = track._reader.unavailable_uri_dummy if track.has_uri else random_uri()

        track.title = "new title"
        track.artist = "new artist"
        track.album = "new album artist"
        track.album_artist = "new various"
        track.track_number = 2
        track.track_total = 3
        track.genres = ["Big Band", "Swing"]
        track.year = 1956
        track.month = 4
        track.day = 16
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

        self.assert_track_tags_equal(track_update_dry, track_original)
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

        self.assert_track_tags_equal(track_update, track_original)
        assert track_update.comments == [new_uri]

        if new_uri == track._reader.unavailable_uri_dummy:
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

        self.assert_track_tags_equal_on_existing(track_update_replace, track_update)
        assert track_update_replace.comments == [new_uri]

        if new_uri == track._reader.unavailable_uri_dummy:
            assert track_update.uri is None
        else:
            assert track_update.uri == new_uri
        assert track_update_replace.image_links == track_update.image_links
        assert track_update_replace.has_image == track_update.has_image

    def test_update_tags_results(self, track: LocalTrack):
        track_original = copy(track)

        track.title = "new title"
        track.album = "new album artist"
        track.track_number += 2
        track.genres = ["Big Band", "Swing"]
        track.year += 10
        track.bpm += 10
        track.key = "F#"
        track.disc_number += 5

        result = track.save(tags=LocalTrackField.ALL, replace=True, dry_run=False)
        assert result.saved

        expected_tags = {
            LocalTrackField.TITLE,
            LocalTrackField.ALBUM,
            LocalTrackField.TRACK,
            LocalTrackField.GENRES,
            (LocalTrackField.DATE if track.tag_map.date else LocalTrackField.YEAR),
            LocalTrackField.BPM,
            LocalTrackField.KEY,
            LocalTrackField.DISC,
        }
        assert set(result.updated) == expected_tags

        self.assert_track_tags_equal(track, deepcopy(track_original))

        track.artist = "new artist"
        track.album_artist = "new various"
        track.compilation = not track.compilation

        tags_to_update = {LocalTrackField.ARTIST, LocalTrackField.COMPILATION}
        result = track.save(tags=tags_to_update, replace=True, dry_run=False)
        assert result.saved
        assert set(result.updated) == tags_to_update

    @staticmethod
    def get_update_image_test_track(track: LocalTrack) -> tuple[LocalTrack, LocalTrack]:
        """Load track and modify its tags for update tags tests"""
        track.image_links = {"cover front": path_track_img}
        return track, copy(track)

    @staticmethod
    def assert_update_image_result(track: LocalTrack, image: Image, result: SyncResultTrack):
        """Check for expected results after non-dry_run operations to update LocalTrack images"""
        assert result.saved

        track.refresh()
        assert track.has_image

        images = track._reader.read_images()
        if not isinstance(track, MP3):
            # MP3 tagging works slightly differently so more than one image will be saved
            assert len(images) == 1
        assert images[0].size == image.size

    def test_update_image_dry_run(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        image_original = track_update._reader.read_images()[0]

        # dry run, no updates should happen
        result = track_update.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=True)
        assert not result.saved

        track_update.refresh()
        assert track_update.has_image == track_original.has_image

        images = track_update._reader.read_images()
        assert len(images) == 1
        assert images[0].size == image_original.size

    def test_update_image_no_replace(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        # clear current image and update
        track_update.delete_tags(LocalTrackField.IMAGES, dry_run=False)
        assert not track_update.has_image

        result = track_update.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=False)
        self.assert_update_image_result(track=track_update, image=open_image(path_track_img), result=result)

    def test_update_image_with_replace(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        result = track_update.save(tags=LocalTrackField.IMAGES, replace=True, dry_run=False)
        self.assert_update_image_result(track=track_update, image=open_image(path_track_img), result=result)
