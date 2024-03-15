from musify.local.playlist import M3U, XAutoPF
from musify.local.track import load_track

tracks = [
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
]

playlist = M3U("<PATH TO AN M3U PLAYLIST>", tracks=tracks)

playlist = M3U("<PATH TO AN M3U PLAYLIST>")
playlist = XAutoPF("<PATH TO AN XAUTOPF PLAYLIST>")

# pretty print information about this playlist
print(playlist)

from musify.local.playlist import load_playlist

playlist = load_playlist("<PATH TO A PLAYLIST>")

from musify.local.track import load_track

tracks = [
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
    load_track("<PATH TO A TRACK>"),
]

playlist = M3U("<PATH TO AN M3U PLAYLIST>", tracks=tracks)

from musify.shared.file import PathMapper

playlist = M3U("<PATH TO AN M3U PLAYLIST>", path_mapper=PathMapper())

from musify.spotify.processors import SpotifyDataWrangler

playlist = M3U("<PATH TO AN M3U PLAYLIST>", remote_wrangler=SpotifyDataWrangler())

# add a track to the playlist
playlist.append(load_track("<PATH TO A TRACK>"))

# add album's and artist's tracks to the playlist using either of the following
playlist.extend(tracks)
playlist += tracks

result = playlist.save(dry_run=False)
print(result)
