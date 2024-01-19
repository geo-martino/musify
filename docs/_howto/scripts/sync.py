from musify.spotify.api import SpotifyAPI
api = SpotifyAPI()

from musify.local.library import LocalLibrary
from musify.spotify.processors.wrangle import SpotifyDataWrangler

local_library = LocalLibrary(
    library_folders=["<PATH TO YOUR LIBRARY FOLDER>", ...],
    playlist_folder="<PATH TO YOUR PLAYLIST FOLDER>",
    # this wrangler will be needed to interpret matched URIs as valid
    remote_wrangler=SpotifyDataWrangler(),
)
local_library.load()

from musify.spotify.processors.processors import SpotifyItemSearcher, SpotifyItemChecker

albums = local_library.albums[:3]

searcher = SpotifyItemSearcher(api=api)
searcher.search(albums)

checker = SpotifyItemChecker(api=api)
checker.check(albums)

from musify.spotify.object import SpotifyTrack

for album in albums:
    for local_track in album:
        remote_track = SpotifyTrack.load(local_track.uri, api=api)

        local_track.title = remote_track.title
        local_track.artist = remote_track.artist
        local_track.date = remote_track.date
        local_track.genres = remote_track.genres
        local_track.image_links = remote_track.image_links

        # alternatively, just merge all tags
        local_track |= remote_track

        # save the track here or...
        local_track.save(replace=True, dry_run=False)

    # ...save all tracks on the album at once here
    album.save_tracks(replace=True, dry_run=False)

from musify.spotify.library import SpotifyLibrary

remote_library = SpotifyLibrary(api=api)
remote_library.load_playlists()

local_playlist = local_library.playlists["<YOUR PLAYLIST'S NAME>"]  # case sensitive
remote_playlist = remote_library.playlists["<YOUR PLAYLIST'S NAME>"]  # case sensitive

# sync the object with Spotify and pretty print info about the reloaded remote playlist
remote_playlist.sync(items=local_playlist, kind="new", reload=True, dry_run=False)
print(remote_playlist)
