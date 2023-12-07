import os
import shutil
import string
from copy import copy, deepcopy
from datetime import datetime
from os.path import join, basename, dirname
from random import choice, randrange, randint

import pytest
from dateutil.relativedelta import relativedelta

from syncify.fields import LocalTrackField
from syncify.local.exception import InvalidFileType
from syncify.local.file import open_image
from syncify.local.track import TRACK_CLASSES, LocalTrack, FLAC, M4A, MP3, WMA
# noinspection PyProtectedMember
from syncify.local.track.base.track import _MutagenMock
from syncify.local.track.base.writer import TagWriter
from syncify.remote.enums import RemoteIDType, RemoteItemType
from tests import path_resources, path_cache, path_txt, random_str
from tests.local import remote_wrangler

path_track_cache = join(path_cache, basename(dirname(__file__)))

path_track_resources = join(path_resources, basename(dirname(__file__)))
path_track_flac = join(path_track_resources, "noise_flac.flac")
path_track_mp3 = join(path_track_resources, "noise_mp3.mp3")
path_track_m4a = join(path_track_resources, "noise_m4a.m4a")
path_track_wma = join(path_track_resources, "noise_wma.wma")
path_track_img = join(path_track_resources, "track_image.jpg")
path_track_all = {path for c in TRACK_CLASSES for path in c.get_filepaths(path_track_resources)}


class_path_map: dict[type[LocalTrack], str] = {
    FLAC: path_track_flac,
    MP3: path_track_mp3,
    M4A: path_track_m4a,
    WMA: path_track_wma,
}


def random_uri(kind: RemoteItemType = RemoteItemType.TRACK) -> str:
    """Generates a random Spotify URI of item type ``kind``"""
    return f"spotify:{kind.name.lower()}:{random_str(RemoteIDType.ID.value, RemoteIDType.ID.value + 1)}"


def random_track(cls: type[LocalTrack] | None = None) -> LocalTrack:
    """Generates a new, random track of the given class."""
    if cls is None:
        cls = choice(tuple(TRACK_CLASSES))
    track = cls.__new__(cls)
    TagWriter.__init__(track, remote_wrangler=remote_wrangler)

    track._file = _MutagenMock()
    track.file.info.length = randint(30, 600)

    track.title = random_str(20, 50)
    track.artist = random_str(20, 50)
    track.album = random_str(20, 50)
    track.album_artist = random_str(20, 50)
    track.track_number = randrange(1, 20)
    track.track_total = randint(track.track_number, 20)
    track.genres = [random_str(20, 50) for _ in range(randrange(7))]
    track.year = randrange(1950, datetime.now().year + 1)
    track.bpm = randint(6000, 15000) / 100
    track.key = choice(string.ascii_uppercase[:7])
    track.disc_number = randrange(1, 8)
    track.disc_total = randint(track.disc_number, 20)
    track.compilation = choice([True, False])
    track.comments = [random_str(20, 50) for _ in range(randrange(3))]

    has_uri = choice([True, False])
    track.uri = random_uri() if has_uri else remote_wrangler.unavailable_uri_dummy

    track._image_links = {}
    track.has_image = False

    track._path = join(
        path_track_cache, f"{str(track.track_number).zfill(2)} - {track.title}" + choice(tuple(track.valid_extensions))
    )

    track.date_added = datetime.now() - relativedelta(days=randrange(8, 20), hours=randrange(1, 24))
    track.last_played = datetime.now() - relativedelta(days=randrange(1, 6), hours=randrange(1, 24))
    track.play_count = randrange(100)
    track.rating = randrange(6)

    return track


def random_tracks(number: int, cls: type[LocalTrack] | None = None) -> list[LocalTrack]:
    """Generates a ``number`` of random tracks of the given class."""
    return [random_track(cls=cls) for _ in range(number)]


def copy_track(track: LocalTrack) -> tuple[str, str]:
    """Copy a track to the test cache, returning the original and copy paths."""
    path_file_base = track.path
    path_file_copy = join(path_track_cache, basename(path_file_base))
    os.makedirs(dirname(path_file_copy), exist_ok=True)

    shutil.copyfile(path_file_base, path_file_copy)

    track._path = path_file_copy
    track.load()

    return path_file_base, path_file_copy


def load_track_test(cls: type[LocalTrack], path: str):
    """Generic test for loading a file to LocalTrack object"""
    track = cls(file=path, available=path_track_all, remote_wrangler=remote_wrangler)

    track_file = track.file

    track._file = track.get_file()
    track_reload_1 = track.file

    track.load()
    track_reload_2 = track.file

    # has actually reloaded the file in each reload
    assert id(track_file) != id(track_reload_1) != id(track_reload_2)

    # raises error on unrecognised file type
    with pytest.raises(InvalidFileType):
        cls(file=path_txt, available=path_track_all, remote_wrangler=remote_wrangler)

    # raises error on files that do not exist
    with pytest.raises(FileNotFoundError):
        cls(
            file=f"does_not_exist.{set(track.valid_extensions).pop()}",
            available=path_track_all,
            remote_wrangler=remote_wrangler
        )


def copy_track_test(cls: type[LocalTrack], path: str):
    """Generic test for copying a LocalTrack object"""
    track = cls(file=path, available=path_track_all, remote_wrangler=remote_wrangler)

    track_from_file = cls(file=track.file, available=path_track_all, remote_wrangler=remote_wrangler)
    assert id(track.file) == id(track_from_file.file)

    track_copy = copy(track)
    assert id(track.file) == id(track_copy.file)
    for key, value in vars(track).items():
        assert value == track_copy[key]

    track_deepcopy = deepcopy(track)
    assert id(track.file) != id(track_deepcopy.file)
    for key, value in vars(track).items():
        assert value == track_deepcopy[key]


def set_and_find_file_paths_test(cls: type[LocalTrack], path: str):
    """Generic test for settings and finding file paths for local track"""
    track = cls(file=path, remote_wrangler=remote_wrangler)
    assert track.path == path

    paths = cls.get_filepaths(path_track_resources)
    assert paths == {path}

    track = cls(file=path.upper(), available=paths, remote_wrangler=remote_wrangler)
    assert track.path == path


def clear_tags_test(cls: type[LocalTrack], path: str):
    """Generic test for clearing tags on a given track."""
    track = cls(file=path, available=path_track_all, remote_wrangler=remote_wrangler)
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    # dry run, no updates should happen
    result = track.delete_tags(tags=LocalTrackField.ALL, dry_run=True)
    assert not result.saved

    track_update_dry = deepcopy(track)

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

    # clear
    result = track.delete_tags(tags=LocalTrackField.ALL, dry_run=False)
    assert result.saved

    track_update = deepcopy(track)

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
    assert track_update_dry.has_uri == track_original.has_uri
    assert not track_update.has_image

    os.remove(path_file_copy)


def update_tags_test(cls: type[LocalTrack], path: str) -> None:
    """Generic test for updating tags on a given track."""
    track = cls(file=path, available=path_track_all, remote_wrangler=remote_wrangler)
    path_file_base, path_file_copy = copy_track(track)
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

    # dry run, no updates should happen
    result = track.save(tags=LocalTrackField.ALL, replace=False, dry_run=True)
    assert not result.saved

    track_update_dry = deepcopy(track)

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

    # update and don't replace current tags (except URI if URI is False)
    shutil.copyfile(path_file_base, path_file_copy)
    result = track.save(tags=LocalTrackField.ALL, replace=False, dry_run=False)
    assert result.saved

    track_update = deepcopy(track)

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
    assert track_update.has_uri == track.has_uri
    assert track_update.has_image == track_original.has_image

    # update and replace
    shutil.copyfile(path_file_base, path_file_copy)
    result = track.save(tags=LocalTrackField.ALL, replace=True, dry_run=False)
    assert result.saved
    track_update_replace = deepcopy(track)

    assert track_update_replace.title == track.title
    assert track_update_replace.artist == track.artist
    assert track_update_replace.album == track.album
    assert track_update_replace.album_artist == track.album_artist
    assert track_update_replace.track_number == track.track_number
    assert track_update_replace.track_total == track.track_total
    assert track_update_replace.genres == track.genres
    assert track_update_replace.year == track.year
    assert track_update_replace.bpm == track.bpm
    assert track_update_replace.key == track.key
    assert track_update_replace.disc_number == track.disc_number
    assert track_update_replace.disc_total == track.disc_total
    assert track_update_replace.compilation == track.compilation
    assert track_update_replace.comments == [new_uri]

    if new_uri == remote_wrangler.unavailable_uri_dummy:
        assert track_update.uri is None
    else:
        assert track_update.uri == new_uri
    assert track_update_replace.image_links == track.image_links
    assert track_update_replace.has_image == track.has_image

    os.remove(path_file_copy)


# noinspection PyProtectedMember
def update_images_test(cls: type[LocalTrack], path: str) -> None:
    """Generic test for updating images on a given track."""
    track = cls(file=path, available=path_track_all, remote_wrangler=remote_wrangler)
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    track._image_links = {"cover_front": path_track_img}
    image_original = track._read_images()[0]
    image_new = open_image(path_track_img)

    # dry run, no updates should happen
    result = track.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=True)
    assert not result.saved

    track_update_dry = deepcopy(track)
    image_update_dry = track_update_dry._read_images()[0]
    assert track_update_dry.has_image == track_original.has_image
    assert image_update_dry.size == image_original.size

    # clear current image and update
    shutil.copyfile(path_file_base, path_file_copy)
    track.delete_tags(LocalTrackField.IMAGES, dry_run=False)
    assert not track.has_image

    result = track.save(tags=LocalTrackField.IMAGES, replace=False, dry_run=False)
    assert result.saved

    track_update = deepcopy(track)
    image_update = track_update._read_images()[0]
    assert track_update.has_image
    assert image_update.size == image_new.size

    # update and replace
    shutil.copyfile(path_file_base, path_file_copy)
    result = track.save(tags=LocalTrackField.IMAGES, replace=True, dry_run=False)
    assert result.saved

    track_update_replace = deepcopy(track)
    image_update_replace = track_update_replace._read_images()[0]
    assert track_update_replace.has_image
    assert image_update_replace.size == image_new.size

    os.remove(path_file_copy)


def all_local_track_tests(cls: type[LocalTrack]):
    """Wrapper for all LocalTrack tests"""
    path = class_path_map[cls]

    load_track_test(cls, path)
    copy_track_test(cls, path)
    set_and_find_file_paths_test(cls, path)
    clear_tags_test(cls, path)
    update_tags_test(cls, path)
    update_images_test(cls, path)
