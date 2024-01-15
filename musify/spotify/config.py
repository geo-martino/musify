from musify.shared.remote.config import RemoteObjectClasses
from musify.spotify.object import SpotifyPlaylist, SpotifyTrack, SpotifyAlbum, SpotifyArtist

SPOTIFY_OBJECT_CLASSES = RemoteObjectClasses(
    playlist=SpotifyPlaylist,
    track=SpotifyTrack,
    album=SpotifyAlbum,
    artist=SpotifyArtist,
)
