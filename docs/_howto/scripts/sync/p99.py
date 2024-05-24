from p4 import *

import asyncio

from musify.libraries.remote.spotify.library import SpotifyLibrary

remote_library = SpotifyLibrary(api=api)
playlist = "<YOUR PLAYLIST'S NAME>"  # case sensitive

asyncio.run(match_albums_to_remote(albums, remote_library.factory))
asyncio.run(sync_albums(albums, remote_library.factory))
asyncio.run(sync_local_library_with_remote(playlist, local_library, remote_library))
