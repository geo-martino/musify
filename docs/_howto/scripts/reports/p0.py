from musify.libraries.local.library import LocalLibrary
from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.library import SpotifyLibrary

local_library = LocalLibrary()

api = SpotifyAPI()
remote_library = SpotifyLibrary(api=api)
