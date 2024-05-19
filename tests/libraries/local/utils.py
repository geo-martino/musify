from os.path import join

from musify.libraries.local.playlist import PLAYLIST_CLASSES, XAutoPF
from musify.libraries.local.playlist.xautopf import REQUIRED_MODULES as REQUIRED_XAUTOPF_MODULES
from musify.libraries.local.track import TRACK_CLASSES
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler
from musify.utils import required_modules_installed
from tests.utils import path_resources


path_track_resources = join(path_resources, "track")
path_track_all: set[str] = {path for c in TRACK_CLASSES for path in c.get_filepaths(path_track_resources)}
path_track_flac = join(path_track_resources, "noise_flac.flac")
path_track_mp3 = join(path_track_resources, "noise_mp3.mp3")
path_track_m4a = join(path_track_resources, "noise_m4a.m4a")
path_track_wma = join(path_track_resources, "noise_wma.wma")
path_track_img = join(path_track_resources, "track_image.jpg")

path_playlist_resources = join(path_resources, "playlist")
path_playlist_all: set[str] = {path for c in PLAYLIST_CLASSES for path in c.get_filepaths(path_playlist_resources)}
if required_modules_installed(REQUIRED_XAUTOPF_MODULES):
    path_playlist_all = {
        path for path in path_playlist_all if not any(path.endswith(ext) for ext in XAutoPF.valid_extensions)
    }

path_playlist_m3u = join(path_playlist_resources, "Simple Playlist.m3u")
path_playlist_xautopf_bp = join(path_playlist_resources, "The Best Playlist Ever.xautopf")
path_playlist_xautopf_ra = join(path_playlist_resources, "Recently Added.xautopf")
path_playlist_xautopf_cm = join(path_playlist_resources, "Complex Match.xautopf")

path_library_resources = join(path_resources, "library")

remote_wrangler = SpotifyDataWrangler()
