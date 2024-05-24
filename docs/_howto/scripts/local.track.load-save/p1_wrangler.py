from musify.libraries.local.track import MP3
from musify.libraries.remote.spotify.processors import SpotifyDataWrangler

track = MP3("<PATH TO AN MP3 TRACK>", remote_wrangler=SpotifyDataWrangler())
