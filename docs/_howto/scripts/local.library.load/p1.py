from p0_local import *

import asyncio

# if you have a very large library, this will take some time...
asyncio.run(library.load())

# ...or you may also just load distinct sections of your library
asyncio.run(library.load_tracks())
asyncio.run(library.load_playlists())

# optionally log stats about these sections
library.log_tracks()
library.log_playlists()

# pretty print an overview of your library
print(library)
