from p3 import *

from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler

playlist = asyncio.run(load_playlist("<PATH TO A PLAYLIST>", remote_wrangler=SpotifyDataWrangler()))
