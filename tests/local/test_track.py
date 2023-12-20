from copy import copy, deepcopy
from datetime import datetime
from os.path import basename, dirname, splitext, getmtime

import pytest

from syncify.abstract.item import Item
from syncify.fields import LocalTrackField
from syncify.local import open_image
from syncify.local.exception import InvalidFileType
from syncify.local.track import LocalTrack, load_track, FLAC, M4A, MP3, WMA
from tests.abstract.item import ItemTester
from tests.local.utils import path_track_all, path_track_img, path_track_resources
from tests.spotify.utils import random_uri
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
    assert track_flac.year == 2020
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
    assert track_flac.bit_depth == 0.016
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
    assert track_mp3.year == 2024
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
    assert track_mp3.size == 411038
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
    assert track_m4a.year == 2021
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
    assert track_m4a.bit_depth == 0.016
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
    assert track_wma.year == 2023
    assert track_wma.bpm == 200.56
    assert track_wma.key == 'D'
    assert track_wma.disc_number == 3
    assert track_wma.disc_total == 4
    assert not track_wma.compilation
    assert track_wma.comments == [track_wma.remote_wrangler.unavailable_uri_dummy]

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


class TestLocalTrack(ItemTester):
    """Run generic tests for :py:class:`LocalTrack` implementations"""

    @staticmethod
    @pytest.fixture
    def item(track: LocalTrack) -> Item:
        return track

    @staticmethod
    def test_does_not_load_other_supported_track_types(track: LocalTrack):
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
        assert id(track.file) != id(track.load())

        # raises error on unrecognised file type
        with pytest.raises(InvalidFileType):
            track.__class__(file=path_txt, available=path_track_all)

        # raises error on files that do not exist
        with pytest.raises(FileNotFoundError):
            track.__class__(file=f"does_not_exist.{set(track.valid_extensions).pop()}", available=path_track_all)

    def test_copy_track(self, track: LocalTrack):
        track_from_file = track.__class__(file=track.file, available=path_track_all)
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
        paths = track.__class__.get_filepaths(tmp_path)
        assert paths == {track.path}
        assert len(track.__class__.get_filepaths(path_track_resources)) == 1

        assert track.__class__(file=track.path.upper(), available=paths).path == track.path

    @staticmethod
    def test_clear_tags_dry_run(track: LocalTrack):
        track_update = track
        track_original = copy(track)

        # when dry run, no updates should happen
        result = track_update.delete_tags(tags=LocalTrackField.ALL, dry_run=True)
        assert not result.saved

        track_update_dry = load_track(track.path, remote_wrangler=track.remote_wrangler)

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

    @staticmethod
    def test_clear_tags(track: LocalTrack):
        track_update = track
        track_original = copy(track)

        result = track_update.delete_tags(tags=LocalTrackField.ALL, dry_run=False)
        assert result.saved

        track_update = load_track(track.path, remote_wrangler=track.remote_wrangler)

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
        new_uri = track.remote_wrangler.unavailable_uri_dummy if track.has_uri else random_uri()

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

        if new_uri == track.remote_wrangler.unavailable_uri_dummy:
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

        if new_uri == track.remote_wrangler.unavailable_uri_dummy:
            assert track_update.uri is None
        else:
            assert track_update.uri == new_uri
        assert track_update_replace.image_links == track_update.image_links
        assert track_update_replace.has_image == track_update.has_image

    @staticmethod
    def get_update_image_test_track(track: LocalTrack) -> tuple[LocalTrack, LocalTrack]:
        """Load track and modify its tags for update tags tests"""
        # noinspection PyProtectedMember
        track._image_links = {"cover_front": path_track_img}
        return track, copy(track)

    def test_update_image_dry_run(self, track: LocalTrack):
        track_update, track_original = self.get_update_image_test_track(track)

        image_original = track_update._read_images()[0]

        # dry run, no updates should happen
        result = track_update.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=True)
        assert not result.saved

        track_update_dry = deepcopy(track_update)
        # noinspection PyProtectedMember
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
