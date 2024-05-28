from p3 import *

from musify.libraries.remote.spotify.processors import SpotifyDataWrangler

playlist = asyncio.run(load_playlist("<PATH TO A PLAYLIST>", remote_wrangler=SpotifyDataWrangler()))
