from p0_local import *

# if you have a very large library, this will take some time...
library.load()

# ...or you may also just load distinct sections of your library
library.load_tracks()
library.load_playlists()

# optionally log stats about these sections
library.log_tracks()
library.log_playlists()

# pretty print an overview of your library
print(library)
