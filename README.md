# Syncify

### A complete local library and Spotify management tool. Main features include:
- Search for and associate local songs to Spotify URIs
- Synchronise local playlists with Spotify playlists
- Update local library metadata and embedded images with Spotify metadata
- Backup and restore track metadata and playlists
- Extract and save embedded images from local library or their associated Spotify tracks


# First time set up

1. Get [Spotify for Developers](https://developer.spotify.com/dashboard/login) access. 
2. Create an app and take note of the **client ID** and **client secret**.
3. Clone the repo and install requirements: `pip install -r requirements.txt`








9. Create a file named **.env** in the package root directory with the following variables or set them in the terminal before running Syncify:
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
10. Authorise the program to access your Spotify user's data: `python main.py auth`
    - Log in to spotify in the browser window and authorise access
    - Paste the link from the address bar into the terminal
>  This package is cross-platform. If you intend to use this package across multiple platforms, it is advised to use the default data folder path in the packages root directory by not defining **DATA_PATH**

> **Note**: Currently, this program only supports .mp3, .flac, .wma, and .m4a files. Image reading/embedding for .wma files is not supported.

# Functions

```sh
python main.py [functions]
```


---

### **Search**
#### Search for local tracks without URI associations and check matches.

This function will attempt to match your local tracks to Spotify tracks and assign a
URI to the *comment* tag of your track's metadata by doing the following:
 - Searches Spotify for the track by using a combination of the title, artist, or album as appropriate 
 - Score the results, taking the highest result according to some internal thresholds
   - If the thresholds are not met, a match is not returned.
 - If a match is found, assign this URI to the track internally.
 - Create temporary playlists for each folder of tracks on Spotify so the user can check the matches.
   - The user may then switch out tracks within the playlist, or manually assign URIs to tracks at this point.
   - The user is prompted for the possible options.
 - Once matches are confirmed by the user, assign the URIs to the *comment* tag of each track.
```sh
python main.py search
```

### **Check**
#### Check all matched URIs in a local library on Spotify. 

Checks each track's URI associations across the user's entire library by creating temporary 
Spotify playlists out of each folder's URI associations.

 - Create temporary playlists for each folder of tracks on Spotify so the user can check the matches.
   - The user may then switch out tracks within the playlist, or manually assign URIs to tracks at this point.
   - The user is prompted for the possible options.
 - Once matches are confirmed by the user, assign the URIs to the *comment* tag of each track.

```sh
python main.py check [options]
```

### **Get Tags**
#### Extract Spotify metadata for all linked tags and update the tags given by some config. 

Load the metadata for the URIs associated with each track and copy Spotify metadata to the track.

```sh 
python main.py get_tags [options]
```

### **Sync Spotify**
#### Synchronise Spotify playlists with local playlists.

Apply changes from local playlists to Spotify playlists by adding extra tracks, or replacing entirely.

```sh
python main.py sync_spotify [options]
```

### **Report**
#### Produce reports on local and Spotify libraries.

- The differences between playlists in local and Spotify libraries
- Tracks that have missing tags in the local library.

```sh
python main.py report [options]
```

### **Backup**
#### Create backups of local and Spotify playlists

Backups contain all metadata for all tracks within a library, and the ordered paths or URIs of 
all tracks in all playlists

```sh
python main.py backup [options]
```

### **Restore**
#### Restore metadata or playlists from local or Spotify library backups. 

Restore based on user's input

```sh
python main.py restore [kind] [mod] [options]
```


### Extract Images
#### Extract and save images from embedded local metadata or Spotify.

NOT YET IMPLEMENTED

```sh
python main.py extract [kind] playlists
```


### Clean up data and logs folder
#### Remove old log or output data folders



```sh
python main.py clean [days] [keep]
```


## Get Info

Print info about tracks, artists, albums, or playlists in the terminal.

#### Function Parameters
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

I developed this program for my own use so that I can share my local playlists with friends online. 
In the process however, the program branched out to a package that now helps me manage other aspects 
of my library through Spotify. I am planning to implement more features in the future, but if there's 
something you would like to see added please do let me know! I'm hoping to make it as general-use as 
possible, so any ideas or contributions you have will be greatly appreciated!

The package is completely open-source and reproducible. Use as you like, but be sure to credit your sources!

If you have any suggestions, wish to contribute, or have any issues to report, please do let me know 
via the issues tab or make a new pull request with your new feature for review. 
Otherwise, I hope you enjoy using Syncify!
