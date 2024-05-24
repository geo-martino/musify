from p3 import *

from musify.libraries.local.track import load_track

tracks = [
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
]

name = "<PATH TO AN M3U PLAYLIST>"  # case sensitive
playlist = M3U(name, tracks=tracks)
