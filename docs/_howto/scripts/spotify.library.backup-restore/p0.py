from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.library import SpotifyLibrary

api = SpotifyAPI()
library = SpotifyLibrary(api=api)
