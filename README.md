# Musify

[![PyPI - Version](https://badge.fury.io/py/musify.svg)](https://badge.fury.io/py/musify)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/musify.svg)](https://pypi.org/project/musify/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/musify)](https://pypi.org/project/musify/)
[![Contributors](https://img.shields.io/github/contributors/geo-martino/musify)](https://github.com/geo-martino/musify/graphs/contributors)
</br>
[![GitHub - Deployment](https://github.com/geo-martino/musify/actions/workflows/deploy.yml/badge.svg)](https://github.com/geo-martino/musify/actions/workflows/deploy.yml)
[![GitHub - Documentation](https://github.com/geo-martino/musify/actions/workflows/documentation.yml/badge.svg)](https://github.com/geo-martino/musify/actions/workflows/documentation.yml)

### A Swiss Army knife for music library management
Supporting local and music streaming service (remote) libraries.
- Extract data for all item types from remote libraries, including following/saved items, such as:
**playlists, tracks, albums, artists, users, podcasts, audiobooks**
- Load local audio files, programmatically manipulate, and save tags/metadata/embedded images
- Synchronise local tracks metadata with its matching track's metadata on supported music streaming services
- Synchronise local playlists with playlists on supported music streaming services
- Backup and restore track tags/metadata and playlists for local and remote libraries
- Extract and save images from remote tracks or embedded in local tracks

## Contents

* [Quick Start](#quick-start)
  * [Spotify](#quick-start-spotify)
  * [Local](#quick-start-local)
  * [Sync local and remote](#quick-start-sync)
* [Currently Supported](#supported)
* [Motivation & Aims](#aims)
* [Author Notes](#notes)

> [!NOTE]  
> This readme provides a brief overview of the program. 
> [Read the docs](https://geo-martino.github.io/musify/) for full reference documentation.

## Installation
Package is listed on PyPI and can be installed as usual through pip.

```bash
pip install musify
python -m pip install musify
```

<a id="quick-start"></a>
## Quick Start

> [!TIP]
> Set up logger to ensure you can see all info reported by the later operations.
> Libraries log info about loaded objects to the custom `STAT` level.
> ```python
> import logging
> from musify.shared.logger import STAT
> logging.basicConfig(format="%(message)s", level=STAT)
> ```

<a id="quick-start-spotify"></a>
### Spotify

> In this example, you will: 
> - Authorise access to the [Spotify Web API](https://developer.spotify.com/documentation/web-api)
> - Load your Spotify library
> - Load some other Spotify objects
> - Add some tracks to a playlist

1. If you don't already have one, create a [Spotify for Developers](https://developer.spotify.com/dashboard/login) account. 
2. [Create an app](https://developer.spotify.com/documentation/web-api/concepts/apps). 
   Select "Web API" when asked which APIs you are planning on using. 
   To use this program, you will only need to take note of the **client ID** and **client secret**.
3. Create a `SpotifyAPI` object and authorise the program access to Spotify data as follows:
   
   > The scopes listed in this example will allow access to read your library data and write to your playlists.
   > See Spotify Web API documentation for more information about [scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes)
   ```python
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
   ```
4. Create a `SpotifyLibrary` object and load your library data as follows:
   ```python
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
   ```
5. Load some Spotify objects using any of the supported identifiers as follows:
   ```python
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
   ```
6. Add some tracks to a playlist in your library, synchronise with Spotify, and log the results as follows:
   
   > **NOTE**: This step will only work if you chose to load either your playlists or your entire library in step 4.
   ```python   
   my_playlist = library.playlists["<YOUR PLAYLIST'S NAME>"]  # case sensitive
   
   # add a track to the playlist
   my_playlist.append(track1)
   
   # add an album to the playlist using either of the following
   my_playlist.extend(album)
   my_playlist += album
   
   # sync the object with Spotify and log the results
   result = my_playlist.sync(dry_run=False)
   library.log_sync(result)
   ```

<a id="quick-start-local"></a>
### Local

> In this example, you will: 
> - Load a local library
> - Modify the tags of some local tracks and save them
> - Modify a local playlist and save it

1. Create one of the following supported `LocalLibrary` objects:

   #### Generic local library
   ```python
   from musify.local.library import LocalLibrary
   
   library = LocalLibrary(
       library_folders=["<PATH TO YOUR LIBRARY FOLDER>", ...],
       playlist_folder="<PATH TO YOUR PLAYLIST FOLDER",
   )
   ```
   
   #### MusicBee
   ```python
   from musify.local.library import MusicBee
   
   library = MusicBee(musicbee_folder="<PATH TO YOUR MUSICBEE FOLDER>")
   ```

2. Load your library:
   ```python
   # if you have a very large library, this will take some time...
   library.load()
   
   # ...or you may also just load distinct sections of your library
   library.load_tracks()
   library.load_playlists()
   
   # optionally log stats about these sections
   library.log_tracks()
   library.log_playlists()
   
   # pretty print an overview of your library
   print(library)
   ```
   
3. Get collections from your library:
   ```python
   playlist = library.playlists["<NAME OF YOUR PLAYLIST>"]  # case sensitive
   album = next(album for album in library.albums if album.name == "<ALBUM NAME>")
   artist = next(artist for artist in library.artists if artist.name == "<ARTIST NAME>")
   folder = next(folder for folder in library.folders if folder.name == "<ALBUM NAME>")
   genre = next(genre for genre in library.genres if genre.name == "<GENRE NAME>")
   
   # pretty print information about the loaded objects
   print(playlist, album, artist, folder, genre, sep="\n")
   ```

4. Get a track from your library using any of the following identifiers:
   ```python
   # get a track via its title
   track = library["<TRACK TITLE>"]  # if multiple tracks have the same title, the first matching one if returned
   
   # get a track via its path
   track = library["<PATH TO YOUR TRACK>"]  # must be an absolute path
   
   # get a track according to a specific tag
   track = next(track for track in library if track.artist == "<ARTIST NAME>")
   track = next(track for track in library if "<GENRE>" in track.genres)
   
   # pretty print information about this track
   print(track)
   ```

5. Change some tags:
   ```python
   from datetime import date
   
   track.title = "new title"
   track.artist = "new artist"
   track.album = "new album"
   track.track_number = 200
   track.genres = ["super cool genre", "awesome genre"]
   track.key = "C#"
   track.bpm = 120.5
   track.date = date(year=2024, month=1, day=1)
   track.compilation = True
   track.image_links.update({
        "cover front": "https://i.scdn.co/image/ab67616d0000b2737f0918f1560fc4b40b967dd4",
        "cover back": "<PATH TO AN IMAGE ON YOUR LOCAL DRIVE>"
   })
   
   # see the updated information
   print(track)
   ```

6. Save the tags to the file:
   ```python
   from musify.local.track.field import LocalTrackField
   
   # you don't have to save all the tags you just modified
   # select which you wish to save first like so
   tags = [
        LocalTrackField.TITLE,
        LocalTrackField.GENRES,
        LocalTrackField.KEY,
        LocalTrackField.BPM,
        LocalTrackField.DATE,
        LocalTrackField.COMPILATION,
        LocalTrackField.IMAGES
   ]
   
   track.save(tags=tags, replace=True, dry_run=False)
   ```

7. Add some tracks to one of your playlists and save it:
   ```python
   my_playlist = library.playlists["<NAME OF YOUR PLAYLIST>"]  # case sensitive
   
   # add a track to the playlist
   my_playlist.append(track)
   
   # add album's and artist's tracks to the playlist using either of the following
   my_playlist.extend(album)
   my_playlist += artist
   
   result = my_playlist.save(dry_run=False)
   print(result)
   ```

<a id="quick-start-sync"></a>
### Sync data between local and remote libraries

> In this example, you will: 
> - Search for local tracks on a music streaming service and assign unique remote IDs to tags in your local tracks
> - Get tags and images for a track from a music stream service and save it them to your local track file
> - Create remote playlists from your local playlists

1. Set up and load at least one local library with a remote wrangler attached, and one remote API object.
   > This guide will use Spotify, but any supported music streaming service can be used in generally the same way. 
   > Just modify the imports as required.
   ```python
   from musify.local.library import LocalLibrary
   from musify.spotify.api import SpotifyAPI
   from musify.spotify.processors.wrangle import SpotifyDataWrangler
   
   local_library = LocalLibrary(
       library_folders=["<PATH TO YOUR LIBRARY FOLDER>", ...],
       playlist_folder="<PATH TO YOUR PLAYLIST FOLDER",
       # this wrangler will be needed to interpret matched URIs as valid
       remote_wrangler=SpotifyDataWrangler(), 
   )
   local_library.load()
   
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
   )
   api.authorise()
   ```

2. Search for tracks and check the results:
   ```python
   from musify.spotify.processors.processors import SpotifyItemSearcher, SpotifyItemChecker
   
   albums = local_library.albums[:3]
   
   searcher = SpotifyItemSearcher(api=api)
   searcher.search(albums)
   
   checker = SpotifyItemChecker(api=api)
   checker.check(albums)
   ```

3. Load the matched tracks, get tags from the music streaming service, and save the tags to the file:
   > **NOTE**: By default, URIs are saved to the `comments` tag.
   ```python
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
   ```
4. Once all tracks in a playlist have URIs assigned, sync the local playlist with a remote playlist:
   ```python
   from musify.spotify.library import SpotifyLibrary
   
   remote_library = SpotifyLibrary(api=api)
   remote_library.load_playlists()
   
   local_playlist = local_library.playlists["<YOUR PLAYLIST'S NAME>"]  # case sensitive
   remote_playlist = remote_library.playlists["<YOUR PLAYLIST'S NAME>"]  # case sensitive
   
   remote_playlist.sync(items=local_playlist, kind="new", reload=True, dry_run=False)
   
   # pretty print info about the reloaded remote playlist
   print(remote_playlist)
   ```

<a id="supported"></a>
## Currently Supported

- **Music Streaming Services**: `Spotify`
- **Audio filetypes**: `.mp3` `.m4a` `.flac` `.wma`
- **Local playlist filetypes**: `.m3u` `.xautopf`
- **Local Libraries**: `MusicBee`

<a id="aims"></a>
## Motivations & Aims

The key aim of this package is to provide a seamless framework for interoperability between all types of music 
libraries whether local or remote. </br>

**This framework should allow for the following key functionality between libraries:**

- Synchronise saved user data including: 
  - playlists data (e.g. name, description, tracks)
  - saved tracks/albums/artists etc.
- Synchronise metadata by allowing users to pull metadata from music streaming services and save this to local tracks
- Provide tools to allow users to move from music streaming services to a local library by semi-automating the process 
of purchasing songs.

**With this functionality, user's should then have the freedom to**:

- Switch between music streaming services with a few simple commands
- Share local playlists and other local library data with friends over music streaming services 
without ever having to use them personally
- Easily maintain a high-quality local library with complete metadata

Ultimately, it is not currently so simple to switch between different types of libraries leading to isolation of 
user's library data. This forces users to be locked into one service or one style of library management. 

**User's should have the freedom to choose how and where they want to listen to their favourite artists.**

Given the near non-existence of income these services provide to artists, user's should have the choice to 
compensate their favourite artists fairly for their work, choosing to switch to other services that do and/or choosing 
not to use music streaming services altogether because of this. Hopefully, by reintroducing this choice to users, 
the music industry will be forced to re-evaluate their complete devaluing of creative work in the rush to chase profits, 
and instead return to a culture of nurturing talent by providing artists with a basic income to survive 
on the work of their craft. One can dream.


<a id="notes"></a>
## Author notes, contributions, and reporting issues

I initially developed this program for my own use so that I can share my local playlists with friends online. 
I have always maintained my own local library well and never saw the need to switch to music 
streaming services after their release. However, as an artist who has released music on all streaming services 
and after listening to the concerns many of the artists I follow have regarding these services, I started to refocus 
this project to be one that aims to break down the barriers between listening experiences for users. 
The ultimate aim being to make managing a local library as easy as any of the major music streaming services, 
allowing users the same conveniences while compensating artists fairly for their work.

If you have any suggestions, wish to contribute, or have any issues to report, please do let me know 
via the issues tab or make a new pull request with your new feature for review. 
Otherwise, I hope you enjoy using Musify!
