from p1 import *


async def update_playlist(name: str, library: SpotifyLibrary) -> None:
    """Update a playlist with the given ``name`` in the given ``library``"""
    tracks = await load_tracks(library.api)
    album = await load_album(library.api)
    await load_library(library)

    my_playlist = library.playlists[name]

    # add a track to the playlist
    my_playlist.append(tracks[0])

    # add an album to the playlist using either of the following
    my_playlist.extend(album)
    my_playlist += album

    # sync the object with Spotify and log the results
    async with library:
        result = await my_playlist.sync(dry_run=False)
    library.log_sync(result)
