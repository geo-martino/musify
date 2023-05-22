import os
import shutil
from os.path import join, basename, dirname, exists
from typing import Tuple

from tests.common import path_resources, path_cache

path_playlist_cache = join(path_cache, basename(dirname(__file__)))

path_playlist_resources = join(path_resources, basename(dirname(__file__)))
path_playlist_m3u = join(path_playlist_resources, "Simple Playlist.m3u")
path_playlist_xautopf_bp = join(path_playlist_resources, "The Best Playlist Ever.xautopf")
path_playlist_xautopf_ra = join(path_playlist_resources, "Recently Added.xautopf")


def copy_playlist_file(path: str) -> Tuple[str, str]:
    """Copy a playlist file to the test cache, returning the original and copy paths."""
    path_file_base = path
    path_file_copy = join(path_playlist_cache, basename(path_file_base))
    if not exists(dirname(path_file_copy)):
        os.makedirs(dirname(path_file_copy))

    shutil.copyfile(path_file_base, path_file_copy)

    return path_file_base, path_file_copy
