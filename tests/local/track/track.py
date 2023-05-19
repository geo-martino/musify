import os
import shutil
import string
from copy import copy, deepcopy
from datetime import datetime
from os.path import join, basename, dirname, exists
from random import choice, randrange, randint
from typing import Tuple, Type, Optional, List

from dateutil.relativedelta import relativedelta

from syncify.enums.tags import TagName
from syncify.local.file import open_image
from syncify.local.track import __TRACK_CLASSES__, LocalTrack
from syncify.spotify import __UNAVAILABLE_URI_VALUE__, IDType
from tests.common import path_resources, path_cache, random_str

path_track_cache = join(path_cache, basename(dirname(__file__)))

path_track_resources = join(path_resources, basename(dirname(__file__)))
path_track_flac = join(path_track_resources, "noise_flac.flac")
path_track_mp3 = join(path_track_resources, "noise_mp3.mp3")
path_track_m4a = join(path_track_resources, "noise_m4a.m4a")
path_track_wma = join(path_track_resources, "noise_wma.wma")
path_track_img = join(path_track_resources, "track_image.jpg")


def random_track(cls: Optional[Type[LocalTrack]] = None) -> LocalTrack:
    if cls is None:
        cls = choice(__TRACK_CLASSES__)
    track = cls.__new__(cls)

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

    track.has_uri = choice([True, False])
    if track.has_uri:
        track.uri = "spotify:track:" + random_str(IDType.ID.value, IDType.ID.value + 1)
    else:
        track.uri = __UNAVAILABLE_URI_VALUE__

    track.image_links = {}
    track.has_image = False

    track.path = join(path_track_cache,
                      f"{str(track.track_number).zfill(2)} - {track.title}" + track.valid_extensions[0])
    track.size = randrange(6000, 10000000)
    track.length = randint(30, 600)
    track.date_modified = datetime.now() - relativedelta(days=randrange(1, 20), hours=randrange(1, 24))

    track.date_added = track.date_modified - relativedelta(days=randrange(1, 20), hours=randrange(1, 24))
    track.last_played = datetime.now() - relativedelta(days=randrange(1, 20), hours=randrange(1, 24))
    track.play_count = randrange(100)
    track.rating = randrange(6)

    return track


def random_tracks(number: int, cls: Optional[Type[LocalTrack]] = None) -> List[LocalTrack]:
    return [random_track(cls=cls) for _ in range(number)]


def copy_track(track: LocalTrack) -> Tuple[str, str]:
    path_file_base = track.path
    path_file_copy = join(path_track_cache, basename(path_file_base))
    if not exists(dirname(path_file_copy)):
        os.makedirs(dirname(path_file_copy))

    shutil.copyfile(path_file_base, path_file_copy)

    track._path = path_file_copy
    track.load()

    return path_file_base, path_file_copy


def clear_tags_test(track: LocalTrack) -> None:
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    # dry run, no updates should happen
    result = track.delete_tags(tags=TagName.ALL, dry_run=True)
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
    result = track.delete_tags(tags=TagName.ALL, dry_run=False)
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


def update_tags_test(track: LocalTrack) -> None:
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    track.title = 'new title'
    track.artist = 'new artist'
    track.album = 'new album artist'
    track.album_artist = 'new various'
    track.track_number = 2
    track.track_total = 3
    track.genres = ['Big Band', 'Swing']
    track.year = 1956
    track.bpm = 98.0
    track.key = 'F#'
    track.disc_number = 2
    track.disc_total = 3
    track.compilation = False
    track.has_uri = False
    track.image_links = None

    # dry run, no updates should happen
    result = track.save(tags=TagName.ALL, replace=False, dry_run=True)
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

    # update and don't replace current tags (except uri if uri is False)
    shutil.copyfile(path_file_base, path_file_copy)
    result = track.save(tags=TagName.ALL, replace=False, dry_run=False)
    assert result.saved if track_original.has_uri else not result.saved

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
    assert track_update.comments == [__UNAVAILABLE_URI_VALUE__]

    assert track_update.uri is None
    assert track_update.has_uri == track.has_uri
    assert track_update.has_image == track_original.has_image

    # update and replace
    shutil.copyfile(path_file_base, path_file_copy)
    result = track.save(tags=TagName.ALL, replace=True, dry_run=False)
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
    assert track_update_replace.comments == [__UNAVAILABLE_URI_VALUE__]

    assert track_update_replace.uri is None
    assert track_update_replace.image_links == track.image_links
    assert track_update_replace.has_image == track.has_image

    os.remove(path_file_copy)


# noinspection PyProtectedMember
def update_images_test(track: LocalTrack) -> None:
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    track.image_links = {"cover_front": path_track_img}
    image_original = track._read_images()[0]
    image_new = open_image(path_track_img)

    # dry run, no updates should happen
    result = track.save(tags=TagName.IMAGES, replace=False, dry_run=True)
    assert not result.saved

    track_update_dry = deepcopy(track)
    image_update_dry = track_update_dry._read_images()[0]
    assert track_update_dry.has_image == track_original.has_image
    assert image_update_dry.size == image_original.size

    # clear current image and update
    shutil.copyfile(path_file_base, path_file_copy)
    track.delete_tags(TagName.IMAGES, dry_run=False)
    assert not track.has_image

    result = track.save(tags=TagName.IMAGES, replace=False, dry_run=False)
    assert result.saved

    track_update = deepcopy(track)
    image_update = track_update._read_images()[0]
    assert track_update.has_image
    assert image_update.size == image_new.size

    # update and replace
    shutil.copyfile(path_file_base, path_file_copy)
    result = track.save(tags=TagName.IMAGES, replace=True, dry_run=False)
    assert result.saved

    track_update_replace = deepcopy(track)
    image_update_replace = track_update_replace._read_images()[0]
    assert track_update_replace.has_image
    assert image_update_replace.size == image_new.size

    os.remove(path_file_copy)
