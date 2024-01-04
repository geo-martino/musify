from syncify.remote.config import RemoteObjectClasses
from syncify.spotify.library.object import SpotifyPlaylist, SpotifyTrack, SpotifyAlbum, SpotifyArtist

SPOTIFY_OBJECT_CLASSES = RemoteObjectClasses(
    playlist=SpotifyPlaylist,
    track=SpotifyTrack,
    album=SpotifyAlbum,
    artist=SpotifyArtist,
)
