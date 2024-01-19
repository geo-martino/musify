from musify.spotify.api import SpotifyAPI

api = SpotifyAPI(
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
    scopes=[
        "user-library-read",
        "user-follow-read",
        "playlist-read-collaborative",
        "playlist-read-private",
        "playlist-modify-public",
        "playlist-modify-private"
    ],
    # providing a `token_file_path` will save the generated token to your system
    # for quicker authorisations in future
    token_file_path="<PATH TO JSON TOKEN>"
)

# authorise the program to access your Spotify data in your web browser
api.authorise()

from musify.spotify.library import SpotifyLibrary

library = SpotifyLibrary(api=api)

# if you have a very large library, this will take some time...
library.load()

# ...or you may also just load distinct sections of your library
library.load_playlists()
library.load_tracks()
library.load_saved_albums()
library.load_saved_artists()

# enrich the loaded objects; see each function's docstring for more info on arguments
# each of these will take some time depending on the size of your library
library.enrich_tracks(features=True, analysis=False, albums=False, artists=False)
library.enrich_saved_albums()
library.enrich_saved_artists(tracks=True, types=("album", "single"))

# optionally log stats about these sections
library.log_playlists()
library.log_tracks()
library.log_albums()
library.log_artists()

# pretty print an overview of your library
print(library)

from musify.spotify.object import SpotifyTrack, SpotifyAlbum, SpotifyPlaylist, SpotifyArtist

# load by ID
track1 = SpotifyTrack.load("6fWoFduMpBem73DMLCOh1Z", api=api)
# load by URI
track2 = SpotifyTrack.load("spotify:track:4npv0xZO9fVLBmDS2XP9Bw", api=api)
# load by open/external style URL
track3 = SpotifyTrack.load("https://open.spotify.com/track/1TjVbzJUAuOvas1bL00TiH", api=api)
# load by API style URI
track4 = SpotifyTrack.load("https://api.spotify.com/v1/tracks/6pmSweeisgfxxsiLINILdJ", api=api)

# load many different kinds of supported Spotify types
playlist = SpotifyPlaylist.load("spotify:playlist:37i9dQZF1E4zg1xOOORiP1", api=api, extend_tracks=True)
album = SpotifyAlbum.load("https://open.spotify.com/album/0rAWaAAMfzHzCbYESj4mfx", api=api, extend_tracks=True)
artist = SpotifyArtist.load("1odSzdzUpm3ZEEb74GdyiS", api=api, extend_tracks=True)

# pretty print information about the loaded objects
print(track1, track2, track3, playlist, album, artist, sep="\n")

my_playlist = library.playlists["<YOUR PLAYLIST'S NAME>"]  # case sensitive

# add a track to the playlist
my_playlist.append(track1)

# add an album to the playlist using either of the following
my_playlist.extend(album)
my_playlist += album

# sync the object with Spotify and log the results
result = my_playlist.sync(dry_run=False)
library.log_sync(result)
