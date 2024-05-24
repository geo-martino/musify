from p3 import *

from musify.libraries.remote.spotify.processors import SpotifyDataWrangler

playlist = M3U("<PATH TO AN M3U PLAYLIST>", remote_wrangler=SpotifyDataWrangler())
