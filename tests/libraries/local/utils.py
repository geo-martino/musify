from pathlib import Path

from musify.libraries.local.playlist import PLAYLIST_CLASSES, XAutoPF
from musify.libraries.local.playlist.xautopf import REQUIRED_MODULES as REQUIRED_XAUTOPF_MODULES
from musify.libraries.local.track import TRACK_CLASSES
from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler
from musify.utils import required_modules_installed
from tests.utils import path_resources

path_track_resources = path_resources.joinpath("track")
path_track_all: set[Path] = {path for c in TRACK_CLASSES for path in c.get_filepaths(path_track_resources)}
path_track_flac = path_track_resources.joinpath("NOISE_FLaC").with_suffix(".flac")
path_track_mp3 = path_track_resources.joinpath("noiSE_mP3").with_suffix(".mp3")
path_track_m4a = path_track_resources.joinpath("noise_m4a").with_suffix(".m4a")
path_track_wma = path_track_resources.joinpath("noise_wma").with_suffix(".wma")
path_track_img = path_track_resources.joinpath("track_image").with_suffix(".jpg")

path_playlist_resources = path_resources.joinpath("playlist")
path_playlist_all: set[Path] = {path for c in PLAYLIST_CLASSES for path in c.get_filepaths(path_playlist_resources)}
if not required_modules_installed(REQUIRED_XAUTOPF_MODULES):
    path_playlist_all = {
        path for path in path_playlist_all if not any(path.suffix == ext for ext in XAutoPF.valid_extensions)
    }

path_playlist_m3u = path_playlist_resources.joinpath("Simple Playlist").with_suffix(".m3u")
path_playlist_xautopf_bp = path_playlist_resources.joinpath("The Best Playlist Ever").with_suffix(".xautopf")
path_playlist_xautopf_ra = path_playlist_resources.joinpath("Recently Added").with_suffix(".xautopf")
path_playlist_xautopf_cm = path_playlist_resources.joinpath("Complex Match").with_suffix(".xautopf")

path_library_resources = path_resources.joinpath("library")

remote_wrangler = SpotifyDataWrangler()
