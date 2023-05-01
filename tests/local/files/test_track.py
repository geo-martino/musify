import os
import shutil
from copy import copy, deepcopy
from os.path import join, basename, dirname, exists
from typing import Tuple

from syncify.local.files._track import Track
from syncify.local.files.tags.helpers import TagEnums
from syncify.spotify.helpers import __UNAVAILABLE_URI_VALUE__
from tests.common import path_cache


def copy_track(track: Track) -> Tuple[str, str]:
    path_file_base = track.path
    path_file_copy = join(path_cache, basename(dirname(__file__)), basename(path_file_base))
    if not exists(dirname(path_file_copy)):
        os.makedirs(dirname(path_file_copy))

    shutil.copyfile(path_file_base, path_file_copy)

    track._path = path_file_copy
    track.load(track.position)

    return path_file_base, path_file_copy


def clear_tags_test(track: Track) -> None:
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    os.remove(path_file_copy)


def update_tags_test(track: Track) -> None:
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
    track.update_file_tags(tags=TagEnums.ALL, replace=False, dry_run=True)
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

    assert track_update_dry.image_links == track_original.image_links
    assert track_update_dry.has_image == track_original.has_image

    # update and don't replace current tags unless uri is False
    shutil.copyfile(path_file_base, path_file_copy)
    track.update_file_tags(tags=TagEnums.ALL, replace=False, dry_run=False)
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

    assert track_update.image_links == track_original.image_links
    assert track_update.has_image == track_original.has_image

    # update and replace
    shutil.copyfile(path_file_base, path_file_copy)
    track.update_file_tags(tags=TagEnums.ALL, replace=True, dry_run=False)
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
    assert track_update_replace.has_uri == track.has_uri

    assert track_update_replace.image_links == track.image_links
    assert track_update_replace.has_image == track.has_image

    os.remove(path_file_copy)


def update_images_test(track: Track) -> None:
    path_file_base, path_file_copy = copy_track(track)
    track_original = copy(track)

    os.remove(path_file_copy)
