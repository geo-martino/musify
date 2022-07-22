# Syncify

### A complete local library and Spotify management tool. Main features include:
- Search for and associate local songs to Spotify URIs
- Syncronise local m3u playlists with Spotify playlists
- Update local library metadata and embedded images with Spotify metadata
- Backup and restore playlists and URI associations
- Extract and save embedded images from local library or their associated Spotify tracks


# First time set up

1. Get [Spotify for Developers](https://developer.spotify.com/dashboard/login) access. 
2. Create an app and take note of the **client ID** and **client secret**.
3. Clone the repo and install requirements: `pip install -r requirements.txt`
4. Create a file named **.env** in the package root directory with the following variables or set them in the terminal before running Syncify:
   - **CLIENT_ID**: From step 2.
   - **CLIENT_SECRET**: From step 2.
   - **WIN_PATH**: Windows specific path to music folder. *(Optional: only 1 path needed)*
   - **MAC_PATH**: Mac specific path to music folder. *(Optional: only 1 path needed)*
   - **LIN_PATH**: Linux specific path to music folder. *(Optional: only 1 path needed)*
   - **PLAYLISTS**: Relative path to folder containing .m3u playlists. Must be a folder in one of the paths above.
   - **DATA_PATH**: Path to folder containing all json files and extracted images. *(Optional: will store to 'data' folder in root of package if not defined)*
   - **TOKEN_FILENAME**: Filename of Spotify access token json file without extension. *(Optional: defaults to token.json)*
   - **ALGORITHM_COMP**: The algorithm level to use for compilation albums. *(Optional: defaults to 4)*
   - **ALGORITHM_ALBUM**: The algorithm level to use for compilation albums. *(Optional: defaults to 2)*
5. Authorise the program to access your Spotify user's data: `python main.py auth`
   - Log in to spotify in the browser window and authorise access
   - Paste the link from the address bar into the terminal
>  This package is cross platform. If you intend to use this package across multiple platforms, it is advised to use the default data folder path in the packages root directory by not defining **DATA_PATH**

> **_NOTE:_** Currently, this program only supports .mp3, .flac, .wma, and .m4a files. Image embedding for .wma files is not supported.

# Primary Functions

```sh
python main.py main [options]
```

The main functionality of Syncify follows the following 13 steps:

> Json filenames denote the file output at each step.

1. Load local library and extract formatted metadata. _**01_library__initial.json**_
2. Search for all tracks that do not have a URI in the expected tag field (default: comment) tag. _**02_report__search.json**_ & _**03_library__searched.json**_
3. Create temporary playlists for any folder that contained missing tracks and add search results. Get usert to check the tracks in these playlists and replace any incorrect matches or add to the playlist for songs that were not matched.
4. Find any songs that have changed or been added to these playlists by the user and match the replaced/missing track to these tracks. 
5. Ask for user input for any tracks still not matched. _**04_report__updated_uris.json**_ & _**05_report__check_matches.json**_
6. Update internal library metadata with new URI tags. _**06_library__checked.json**_
7. Extract metadata from Spotify for all songs in local library that have a URI matched. _**07_spotify__library.json**_
8. Update the stored tags in local tracks based on extracted Spotify metadata. _**08_library__updated.json**_
9. Load local library again, extract formatted metadata and create a backup of the path: URIs. _**09_library__final.json**_ & _**URIs.json**_
10. Extract metadata for all local playlists and create a backup.  _**10_playlists__local.json**_ & _**URIs__local_playlists.json**_
11. Extract Spotify metadata for all Spotify playlists. _**11_playlists__spotify_intial.json**_
12. Update Spotify playlists based on tracks in local playlists. _**12_playlists__spotify_final.json**_
13. Produce a report on the differences between local and Spotify playlists. _**13_report__differences.json**_

> The user may also set options to modify the behvaiour at various steps. See [options](#options) below or by running: `python main.py -h`

---

**The user may also run the following functions which only run specific sets of steps in the main function.**


### **Search**: Load local library, search for tracks and check matches. 
> *Runs steps 1-6 of main function.* **Note: does not update any tags like in step 8**
```sh
python main.py search [options]
```

### **Check**: Load local library and check all matched URIs on Spotify. 
> *Steps 3-8 {only updates URIs in step 7)*
```sh
python main.py check [options]
```

### **Update Tags**: Extract Spotify metadata for all linked tags and update the tags given by the `-t` option. 
> *Runs steps 7-9 of main function.*
```sh
python main.py update_tags [options]
```

### **Update Spotify**: Update Spotify playlists from track lists in local playlists.
> *Runs steps 10-12 of main function*
```sh
python main.py update_spotify [options]
```

### **Report**: Produce a report on the differences between local and Spotfify playlists.
> *Runs step 13 of main function*
```sh
python main.py report [options]
```


# Other Functions

## Missing Tags

Save a report for tracks that have the missing tags defined with the `-t` option to _**14_library__missing_tags.json**_

### Function Parameters
- **match**: ["all", "any"] - Only return tracks that are missing "all" or "any" tags.

```sh
python main.py missing_tags [match] [options]
```


## Backup/Restore

**Backup** - Create backups for the following items:
- _**backup__local_library_URIs.json**_ | Local library metadata with associated URIs in the form **path** - **URI**
- _**backup__local_playlists.json**_ | Local library playlists in the form **playlist name** - \[**track metadata**\]
- _**backup__spotify_playlists.json**_| Spotify playlist metadata in the form **playlist name** - \[**track metadata**\]

```sh
python main.py backup [options]
```

**Restore** - Restore URIs in local library metadata, m3u playlists, or Spotify playlists from these backups.

### Function Parameters
- **kind**: ["local", "spotify"] - The type backup to restore
- **mod**: - If kind='local', restore playlists from local backup if 'playlists', or restore playlists from 'spotify' playlist backup.

```sh
python main.py restore [kind] [mod] [options]
```


## Extract Images
Extract and save images from local metadata or Spotify. By default, sorts by folder name for local, or by album name for Spotify unless **playlists** is set.

### Function Parameters
- **kind**: ["local", "spotify"] - The source of images.
- **playlists**: - If set, only extract images for playlists and store in folders per playlist.

```sh
python main.py extract [kind] playlists
```


## Clean up data and logs folder

### Function Parameters
- **days**: ["local", "spotify"] - Maximum age of files allowed
- **keep**: - Minimum number of files/folders to keep

```sh
python main.py clean [days] [keep]
```


## Create a Spotify Playlist for the current user

### Function Parameters
- **playlist_name** - Name of the playlist
- **public**:  ["True", "False"] - Set playlist as public if True, or private if False
- **collaborative**:  ["True", "False"] - Set playlist as collaborative if True, or private if False

```sh
python main.py create [playlist_name] [public] [collaborative]
```


## Delete a Spotify Playlist from the current user

### Function Parameters
- **playlist** - Playlist name/URI/URL to delete
  
```sh
python main.py delete [playlist]
```


## Clear a Spotify Playlist for the current user

### Function Parameters
- **playlist** - Playlist name to create

```sh
python main.py clear [playlist]
```


## Get Info

Print info about tracks, artists, albums, or playlists in the terminal.

### Function Parameters
- **name** - Accepts name of a user's playlist, or artist/album/playlist URI/URL.

```sh
python main.py get [name] [options]
```


# Options

The following options can be set and applied to many function for various desired results.

## Local library filters and options
- `-q`, `--quickload`: Skip parts of main function and use a previous loads data. If set, use last run's data for these sections or enter a date to define which run to load from. The following logic applies:
  - If latest output is from step 9, load data and start from step 10.
  - If latest output is from step 6, load data and start from step 7
  - Else, attempt to load data from step 2 and proceed to check search results with temporary playlists.
- `-s`, `--start`: When loading local library, prefix of the folder name to start loading from. *(case-insensitive)*
- `-e`, `--end`: When loading local library, prefix of the folder name to stop loading at. *(case-insensitive)*
- `-l`, `--limit`: When loading local library, only include folders with this prefix. *(case-insensitive)*
- `-c`, `--compilation`: Only process albums which are compilation albums as set by the compilation tag.
  
## Spotify metadata extraction options
- `-ag`, `--add-genre`: Add genre metadata to results by querying artist data
- `-af`, `--add-features`: Add audio features metadata to results
- `-aa`, `--add-analysis`: Add audio features analysis to results
- `-ar`, `--add-raw`: Keep raw data returned from Spotify for all tracks under 'raw_data' key. 
   > **Warning**: This increases load time significantly as this endpoint only allows track-by-track queries.
  
## Playlist processing options
- `-in`, `--in-playlists`: Only process playlists in this list *(case-insensitive)*
- `-ex`, `--ex-playlists`: Exclude all playlists in this list *(case-insensitive)*
- `-f`, `--filter`: Path to a json file containing tag values to exclude when adding songs to Spotify playlists. Default path: _**{DATA_PATH}/filter.json**_. Example:
  ```json
   {
      "artist": [
         "r. kelly",
      ],
      "album": [
         "downloads",
      ]
   }
  ```
- `-ce`, `--clear-extra`: When clearing Spotify playlists, only clear songs that are not in local playlists.
- `-ca`, `--clear-all`: When clearing Spotify playlists, clear all tracks in the playlist.
  
## Local library tag update options
- `-t`, `--tags`: A list of tags to process when processing local metadata.
- `-r`, `--replace`: If set, destructively replaces metadata in local files when updating tag. Default behaviour only updates metadata for which there is no value currently present.

## Runtime options
- `-o`, `--no-output`: Suppress all json file output, apart from files saved to the parent folder i.e. API token file and URIs.json.
- `-v`, `--verbose`: Add additional stats on libraries to terminal output throughout the run
- `-x`, `--execute`: Modify users files and playlist. By default, Syncify will not affect any files or playlists and append '_dry' to data folder path.



# Author notes, contributions, and reporting issues

I developed this program for my own use so I can share my local playlists with friends online. In the process however, the program branched out to a package that now helps me manage other aspects of my library through Spotify. I am planning to implement more features in the future, but if there's something you would like to see added please do let me know! I'm hoping to make it as general-use as possible, so any ideas or contributions you have will be greatly appreciated!

The package is completely open-source and reproducible. Use as you like, but be sure to credit your sources!

If you have any suggestions, wish to contribute, or have any issues to report, please do let me know via the issues tab or make a new pull request with your new feature for review. Otherwise, I hope you enjoy using Syncify!
