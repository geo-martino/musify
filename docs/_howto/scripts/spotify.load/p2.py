from p1 import *

from musify.libraries.remote.spotify.library import SpotifyLibrary


async def load_library(api: SpotifyAPI) -> SpotifyLibrary:
    library = SpotifyLibrary(api=api)

    # authorise the program to access your Spotify data in your web browser
    async with api:
        # if you have a very large library, this will take some time...
        await library.load()

        # ...or you may also just load distinct sections of your library
        await library.load_playlists()
        await library.load_tracks()
        await library.load_saved_albums()
        await library.load_saved_artists()

        # enrich the loaded objects; see each function's docstring for more info on arguments
        # each of these will take some time depending on the size of your library
        await library.enrich_tracks(features=True, analysis=False, albums=False, artists=False)
        await library.enrich_saved_albums()
        await library.enrich_saved_artists(tracks=True, types=("album", "single"))

    # optionally log stats about these sections
    library.log_playlists()
    library.log_tracks()
    library.log_albums()
    library.log_artists()

    # pretty print an overview of your library
    print(library)

    return library
