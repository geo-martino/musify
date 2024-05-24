from p2 import *


async def update_playlist(spotify_api: SpotifyAPI) -> None:
    tracks = await load_tracks(spotify_api)
    album = await load_album(spotify_api)
    library = await load_library(spotify_api)

    my_playlist = library.playlists["test"]  # case sensitive

    # add a track to the playlist
    my_playlist.append(tracks[0])

    # add an album to the playlist using either of the following
    my_playlist.extend(album)
    my_playlist += album

    # sync the object with Spotify and log the results
    async with spotify_api:
        result = await my_playlist.sync(dry_run=False)
    library.log_sync(result)
