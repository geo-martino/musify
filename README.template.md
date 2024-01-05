# Syncify

### A complete local and music streaming service (remote) library management tool.
- Extract data for all item types from remote libraries, including following/saved items, such as:
**playlists, tracks, albums, artists, users, podcasts, audiobooks**
- Load local audio files, programmatically manipulate, and save tags/metadata/embedded images
- Synchronise local tracks metadata with its matching track's metadata on supported music streaming services
- Synchronise local playlists with playlists on supported music streaming services
- Backup and restore track tags/metadata and playlists for local and remote libraries
- Extract and save images from remote tracks or embedded in local tracks

## Contents

* [Quick Start Guides](#quick-start-guides)
  * [Spotify](#quick-start-spotify)
  * [Local](#quick-start-local)
* [Currently Supported](#currenty-supported)

## Quick Start Guides

> [!TIP]
> Set up logger to ensure you can see all info reported by the later operations.
> Libraries log info about loaded objects to the custom `REPORT` level.
> ```python
> import logging
> logging.basicConfig(format="%(message)s", level=logging.REPORT)
> ```

<a id="quick-start-spotify"></a>
### Spotify

1. Get [Spotify for Developers](https://developer.spotify.com/dashboard/login) access. 
2. Create an app and take note of the **client ID** and **client secret**.
3. Create a `SpotifyAPI` object and load your `SpotifyLibrary`:
    > **NOTE**: See Spotify Web API documentation for available [scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes)
    ```python
    from syncify.spotify.api import SpotifyAPI
    from syncify.spotify.library import SpotifyLibrary
    
    api = SpotifyAPI(
       client_id="<YOUR CLIENT ID>",
       client_secret="<YOUR CLIENT SECRET>",
       scopes=[
           "user-library-read",
           "user-follow-read",
           "playlist-read-collaborative",
           "playlist-read-private"
       ],
       # providing a `token_file_path` will save the generated token to your system 
       # for quicker authorisations in future
       token_file_path="<PATH TO JSON TOKEN>"  
    )
   
    # authorise the program to access your Spotify data in your web browser
    api.authorise()
    
    library = SpotifyLibrary(api=api)
   
    # if you have a very large library, this will take some time...
    library.load()
    
    # ...or you may also just load distinct sections of your library as follows
    library.load_playlists()
    library.load_saved_tracks()
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
    ```
4. Load some Spotify objects using any of the supported identifiers:
    ```python
    from syncify.spotify.object import SpotifyTrack, SpotifyAlbum, SpotifyPlaylist, SpotifyArtist
    
    # load objects by ID
    track1 = SpotifyTrack.load("6fWoFduMpBem73DMLCOh1Z", api=api)
    # load objects by URI
    track2 = SpotifyTrack.load("spotify:track:4npv0xZO9fVLBmDS2XP9Bw", api=api)
    # load objects by open/external style URL
    track3 = SpotifyTrack.load("https://open.spotify.com/track/1TjVbzJUAuOvas1bL00TiH", api=api)
    # load objects by API style URI
    track4 = SpotifyTrack.load("https://api.spotify.com/v1/tracks/6pmSweeisgfxxsiLINILdJ", api=api)
    
    album = SpotifyAlbum.load("https://open.spotify.com/album/0rAWaAAMfzHzCbYESj4mfx", api=api, extend_tracks=True)
    playlist = SpotifyPlaylist.load("spotify:playlist:37i9dQZF1E4zg1xOOORiP1", api=api, extend_tracks=True)
    artist = SpotifyArtist.load("1odSzdzUpm3ZEEb74GdyiS", api=api, extend_tracks=True) 
    
    # pretty print information about the loaded objects
    print(track1, track2, track3, album, playlist, artist)
    ```
5. Add some tracks to a playlist in your library, synchronise with Spotify, and log the results
   (assuming you chose to load your entire library or your just your playlists in step 3).
    ```python   
    my_playlist = library.playlists["<YOUR PLAYLIST'S NAME>"]
    my_playlist.append(track1)
    my_playlist.extend(album)
   
    results = library.sync(dry_run=False)
    library.log_sync(results)
    ```

<a id="quick-start-local"></a>
### Local
More documentation to come...



## Currently Supported

- **Music Streaming Services**: {remote_sources}
- **Audio filetypes**: {track_filetypes}
- **Local playlist filetypes**: {playlist_filetypes}
- **Local Libraries**: {local_sources}


## Author notes, contributions, and reporting issues

I developed this program for my own use so that I can share my local playlists with friends online. 
In the process however, the program branched out to a package that now helps me manage other aspects 
of my music libraries. I am planning to implement more features in the future, but if there's 
something you would like to see added please do let me know! I'm hoping to make it as general-use as 
possible, so any ideas or contributions you have will be greatly appreciated.

If you have any suggestions, wish to contribute, or have any issues to report, please do let me know 
via the issues tab or make a new pull request with your new feature for review. 
Otherwise, I hope you enjoy using Syncify!
