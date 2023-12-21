from abc import ABCMeta
from os.path import join, basename, dirname

from tests.abstract.collection import PlaylistTester
from tests.local.test_local_collection import LocalCollectionTester
from tests.utils import path_resources

path_playlist_resources = join(path_resources, str(basename(dirname(__file__))))
path_playlist_m3u = join(path_playlist_resources, "Simple Playlist.m3u")
path_playlist_xautopf_bp = join(path_playlist_resources, "The Best Playlist Ever.xautopf")
path_playlist_xautopf_ra = join(path_playlist_resources, "Recently Added.xautopf")


class LocalPlaylistTester(PlaylistTester, LocalCollectionTester, metaclass=ABCMeta):
    pass
