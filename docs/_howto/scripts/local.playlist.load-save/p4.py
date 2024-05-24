from p3 import *

# add a track to the playlist
playlist.append(load_track("<PATH TO A TRACK>"))

# add album's and artist's tracks to the playlist using either of the following
playlist.extend(tracks)
playlist += tracks
