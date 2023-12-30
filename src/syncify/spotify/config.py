from syncify.remote.config import RemoteObjectClasses
from syncify.spotify.library.object import SpotifyTrack, SpotifyAlbum, SpotifyPlaylist

SPOTIFY_OBJECT_CLASSES = RemoteObjectClasses(
    track=SpotifyTrack,
    album=SpotifyAlbum,
    playlist=SpotifyPlaylist,
)
