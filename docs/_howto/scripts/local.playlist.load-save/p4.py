from p3 import *

# add a track to the playlist
track = asyncio.run(load_track("<PATH TO A TRACK>"))
playlist.append(track)

# add album's and artist's tracks to the playlist using either of the following
playlist.extend(tracks)
playlist += tracks
