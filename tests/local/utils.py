from os.path import join

from musify.local.track import TRACK_CLASSES
from musify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.utils import path_resources

path_track_resources = join(path_resources, "track")
path_track_flac = join(path_track_resources, "noise_flac.flac")
path_track_mp3 = join(path_track_resources, "noise_mp3.mp3")
path_track_m4a = join(path_track_resources, "noise_m4a.m4a")
path_track_wma = join(path_track_resources, "noise_wma.wma")
path_track_img = join(path_track_resources, "track_image.jpg")
path_track_all: set[str] = {path for c in TRACK_CLASSES for path in c.get_filepaths(path_track_resources)}

remote_wrangler = SpotifyDataWrangler()
