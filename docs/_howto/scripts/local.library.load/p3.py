from p2 import *

# get a track via its title
track = library["<TRACK TITLE>"]  # if multiple tracks have the same title, the first matching one if returned

# get a track via its path
track = library["<PATH TO YOUR TRACK>"]  # must be an absolute path

# get a track according to a specific tag
track = next(track for track in library if track.artist == "<ARTIST NAME>")
track = next(track for track in library if "<GENRE>" in (track.genres or []))

# pretty print information about this track
print(track)
