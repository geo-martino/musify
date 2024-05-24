from musify.libraries.local.playlist import M3U
from musify.libraries.local.track import load_track

tracks = [
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
]

playlist = M3U("<PATH TO AN M3U PLAYLIST>", tracks=tracks)
