# Documentation<a id="top"></a>

- [**Syncify**](#syncify)
	* [\_\_init\_\_](#init)
	* [set_env](#set_env)
	* [load_all_local](#load_all_local)
	* [load_all_spotify](#load_all_spotify)
	* [load_m3u](#load_m3u)
	* [load_spotify](#load_spotify)
	* [update_uri_from_spotify_playlists](#update_uri_from_spotify_playlists)
	* [search_m3u_to_spotify](#search_m3u_to_spotify)
	* [differences](#differences)
	* [update_artwork](#update_artwork)
	* [get_missing_uri](#get_missing_uri)
	* [spotify_to_tag](#spotify_to_tag)
- [**Data**](#data)
	* [load_file](#load_file)
	* [get_m3u_metadata](#get_m3u_metadata)
	* [get_all_metadata](#get_all_metadata)
	* [get_song_metadata](#get_song_metadata)
	* [import_uri](#import_uri)
	* [export_uri](#export_uri)
	* [save_json](#save_json)
	* [load_json](#load_json)
	* [uri_as_key](#uri_as_key)
	* [missing_tags](#missing_tags)
	* [update_tags](#update_tags)
	* [rebuild_uri_from_tag](#rebuild_uri_from_tag)
- [**Process**](#process)
	* [extract_images](#extract_images)
	* [embed_images](#embed_images)
	* [caps](#caps)
	* [titlecase_folders](#titlecase_folders)
	* [titlecase_files](#titlecase_files)
	* [tags_from_filename](#tags_from_filename)
- [**Spotify**](#spotify)
	* [get_playlists_metadata](#get_playlists_metadata)
	* [get_tracks_metadata](#get_tracks_metadata)
	* [extract_track_metadata](#extract_track_metadata)
	* [update_uris](#update_uris)
	* [update_playlist](#update_playlist)
	* [get_differences](#get_differences)
	* [check_uris_on_spotify](#check_uris_on_spotify)
- [**Search**](#search)
	* [search_all](#search_all)
	* [get_track_match](#get_track_match)
	* [get_album_match](#get_album_match)
	* [clean_tags](#clean_tags)
	* [quick_match](#quick_match)
	* [deep_match](#deep_match)
- [**Endpoints**](#endpoints)
	* [convert](#convert)
	* [get_request](#get_request)
	* [search](#search)
	* [get_user](#get_user)
	* [get_tracks](#get_tracks)
	* [get_all_playlists](#get_all_playlists)
	* [get_playlist_tracks](#get_playlist_tracks)
	* [create_playlist](#create_playlist)
	* [delete_playlist](#delete_playlist)
	* [clear_playlist](#clear_playlist)
	* [add_to_playlist](#add_to_playlist)
	* [uri_from_link](#uri_from_link)
- [**Authorise**](#authorise)
	* [auth](#auth)
	* [refresh_token](#refresh_token)
	* [get_token_user](#get_token_user)
	* [get_token_basic](#get_token_basic)
	* [load_spotify_token](#load_spotify_token)
	* [save_spotify_token](#save_spotify_token)

[Back to top](#top)
## *class* **Syncify** *(Data, Spotify)*<a id="syncify"></a>

Main class for the entire package. Instantiates all objects.

* [\_\_init\_\_](#init)
* [set_env](#set_env)
* [load_all_local](#load_all_local)
* [load_m3u](#load_m3u)
* [load_spotify](#load_spotify)
* [update_uri_from_spotify_playlists](#update_uri_from_spotify_playlists)
* [search_m3u_to_spotify](#search_m3u_to_spotify)
* [differences](#differences)
* [update_artwork](#update_artwork)
* [get_missing_uri](#get_missing_uri)

### **\_\_init\_\_** *(self, base_api=None, base_auth=None, open_url=None, c_id=None, c_secret=None, music_path=None, playlists=None, win_path=None, mac_path=None, lin_path=None, data=None, uri_file=None, token_file=None, verbose=False, auth=True)*<a id="init"></a>

> *Parameters*
> - base_api: str, default=None. Base link to access Spotify API.
> - base_auth: str, default=None. Base link to authorise through Spotify API.
> - open_url: str, default=None. Base link for user facing links to Spotify items.
> - c_id: str, default=None. ID of developer API access.
> - c_secret: str, default=None. Secret code for developer API access. 
> > 
> - music_path: str, default=None. Base path to all music files.
> - playlists: str, default=None. Relative path to folder containing .m3u playlists, must be in music folder.
> - win_path: str, default=None. Windows specific path to all music files.
> - mac_path: str, default=None. Mac specific path to all music files.
> - lin_path: str, default=None. Linux specific path to all music files.
> >
> - data: str, default=None. Path to folder containing json and image files.
> - uri_file: str, default=None. Filename of URI json file.
> - token_file: str, default=None. Filename of Spotify access token json file.
> >
> - verbose: bool, default=False. Print extra information and persist progress bars if True.
> - auth: bool, default=True. Perform initial authorisation on instantiation if True


### **set_env** *(self, current_state=True, \*\*kwargs)*<a id="set_env"></a>

Save settings to default environment variables. Loads any saved variables and updates as appropriate.

> *Parameters*
> - current_state: bool, default=True. Use current object variables to update.
> - **kwargs: pass kwargs for variables to update. Overrides current_state if True.

> *Return*: dict. Dict of the variables saved.


### **load_all_local** *(self, ex_playlists=None, ex_folders=None, in_folders=None)*<a id="load_all_local"></a>

Loads metadata from all local songs to the object, exports this json to the data folder with filename 'all_metadata.json', and imports URIs from user-defined URIs.json file.

> *Parameters*
> - ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder. Excludes every song from playlists in the default playlist path if True. Ignored if None.
> - ex_folders: list, default=None. Exclude songs in these folders. Ignored if None.
> - in_folders: list, default=None. Only include songs in these folders. Ignored if None.

> *Return*: self.


### **load_all_spotify** *(self, ex_playlists=None, ex_folders=None, in_folders=None)*<a id="load_all_spotify"></a>

Checks API authorisation, runs ***load_all_local***, gets Spotify metadata from the URIs associated to all local files and exports this json to the data folder with filename 'all_spotify_metadata.json'.

> *Parameters*
> - ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder. Excludes every song from playlists in the default playlist path if True. Ignored if None.
> - ex_folders: list, default=None. Exclude songs in these folders. Ignored if None.
> - in_folders: list, default=None. Only include songs in these folders. Ignored if None.

> *Return*: self.


### **load_m3u** *(self, in_playlists=None)*<a id="load_m3u"></a>

Loads metadata from all local playlists to the object, exports this json to the data folder 
with filename 'm3u_metadata.json', and imports URIs from user-defined URIs.json file.

> *Parameters*
> - in_playlists: list, default=None. List of playlist names to include, returns all if None.

> *Return*: self.


### **load_spotify** *(self, in_playlists=None)*<a id="load_spotify"></a>

Checks API authorisation and loads metadata from all Spotify playlists to the object.

> *Parameters*
> - in_playlists: str/list, default=None. List of playlist names to include, returns all if None. Only returns matching local playlist names if 'm3u'.

> *Return*: self.


### **update_uri_from_spotify_playlists** *(self)*<a id="update_uri_from_spotify_playlists"></a>

Update URIs for local files from Spotify playlists.
Loads m3u and Spotify playlists to object if they have not been loaded.

> *Return*: self.


### **search_m3u_to_spotify** *(self, quick_load=False, refresh=False)*<a id="search_m3u_to_spotify"></a>

Search for URIs for local files that don't have one associated, and update Spotify with new URIs.
Saves json file for found songs ('search_found.json'), songs added to playlists ('search_added.json'),
and songs that still have no URI ('search_not_found.json').
Loads m3u and Spotify playlists to object if they have not been loaded.

> *Parameters*
> - quick_load: bool, default=False. Load last search from 'search_found.json' file
> - refresh: bool, default=False. Clear Spotify playlists before updating.

> *Return*: self.


### **differences** *(self)*<a id="differences"></a>

Produces reports on differences between Spotify and local playlists.
Saves reports for songs on Spotify not found in local playlists 'spotify_extra.json',
and local songs with missing URIs and therefore not in Spotify playlists 'spotify_missing.json'.

> *Return*: self.


### **update_artwork** *(self, album_prefix=None, replace=False, report=True)*<a id="update_artwork"></a>

Update locally embedded images with associated URIs' artwork.

> *Parameters*
> - album_prefix: str, default=None. If defined, only replace artwork for albums that start with this string.
> - replace: bool, default=False. Replace locally embedded images if True. Otherwise, only add images to files with no embedded image.
> - report: bool, default=True. Export 'no_images.json' file with information on which files had missing images before running the program.

> *Return*: self.


### **get_missing_uri** *(self, ex_playlists=False, quick_load=False, import_uri=True, drop=True, null_folders=None, start_folder=None, add_back=False, tags=None)*<a id="get_missing_uri"></a>

Search for URIs for files missing them and review through Spotify by means of creating and manually 
checking temporary playlists.

> *Parameters*
> - ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder. Excludes every song from playlists in the default playlist path if True. Ignored if None.
> - quick_load: bool, default=False. Load last search from 'search_found.json' file
> - import_uri: bool, default=True. Import associated URIs for each local song.
> - drop: bool, default=True. If import_uri is True, remove any song that doesn't have a URI, hence skipping a search for new URIs.
> - null_folders: list, default=None. Give all songs in these folders the URI value of 'None', hence skipping all searches and additions to playlist for these songs. Useful for albums not on Spotify.
> - start_folder: str, default=None. Start creation of temporary playlists from this folder.
> - add_back: bool, default=False. Add back tracks which already have URIs on input. False returns only search results.
> - tags: list, default=None. List of tags to update for local song metadata.

> *Return*: self.   


### **spotify_to_tag** *(self, tags, metadata=None, reduce=True, refresh=False)*<a id="spotify_to_tag"></a>

Updates local file tags with tags from Spotify metadata. Tag names for each file extension viewable in self.filetype_tags\[FILE_EXT\].keys()

> *Parameters*
> - tags: list. List of tags to update.
> - metadata: dict, default=None. Metadata of songs to update in form <URI>: <Spotify metadata>
> - reduce: bool, default=True. Reduce the list of songs to update to only those with missing tags.
> - refresh: bool, default=False. Destructively replace tags in each file.


[Back to top](#top)
## *class* **Data** *(Process)*<a id="data"></a>

Methods for loading, saving, and analysing local data.

* [get_m3u_metadata](#get_m3u_metadata)
* [get_all_metadata](#get_all_metadata)
* [get_song_metadata](#get_song_metadata)
* [import_uri](#import_uri)
* [export_uri](#export_uri)
* [save_json](#save_json)
* [load_json](#load_json)
* [uri_as_key](#uri_as_key)
* [no_images](#no_images)


### **load_file** *(self, song)*<a id="load_file"></a>

Load local file using mutagen and extract file extension as string. Searches for case-insensitive path if file is not found from given path.

> *Parameters*
> - song: str or dict. A string of the song's path or a dict containing 'path' as key

> *Return*: (object, str). Mutagen file object and file extension as string.


### **get_m3u_metadata** *(self, in_playlists=None, verbose=True)*<a id="get_m3u_metadata"></a>

Get metadata on all songs found in m3u playlists

> *Parameters*
> - in_playlists: list, default=None. List of playlist names to include, returns all if None.
> - verbose: bool, default=True. Print extra info on playlists and persist progress bars if True.

> *Return*: dict. {\<playlist name\>: \<list of tracks metadata\>}


### **get_all_metadata** *(self, ex_playlists=None, ex_folders=None, in_folders=None, verbose=True)*<a id="get_all_metadata"></a>

Get metadata on all audio files in music folder.

> *Parameters*
> - ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder. Excludes every song from playlists in the default playlist path if True. Ignored if None.
> - ex_folders: list, default=None. Exclude songs in these folders. Ignored if None.
> - in_folders: list, default=None. Only include songs in these folders. Ignored if None.
> - verbose: bool, default=True. Print extra runtime info and persist progress bars if True.

> *Return*: dict. {\<folder name\>: \<list of tracks metadata\>}


### **get_song_metadata** *(self, path, position=None, verbose=True, playlist=None)*<a id="get_song_metadata"></a>

Extract metadata for a song.

> *Parameters*
> - path: str. Path to the song (may be case-insensitive)
> - position: int, default=None. Position of song in a playlist.
> - verbose: bool, default=True. Print error messages if True.
> - playlist: str, default=None. Playlist name to print in error message if verbose == True.

> *Return*: dict. Metadata dict: position, title, artist, album, track, genre, year, length, has_image, path.


### **import_uri** *(self, local, fileid='URIs')*<a id="import_uri"></a>

Import URIs from stored json file. File must be in format {\<album name: {\<title\>: \<URI\>}} format.

> *Parameters*
> - local: dict. Metadata in form {\<name\>: \<dict of metadata incl. path, and album\>}
> - filename: str, default='URIs'. Filename of file to import from data path.

> *Return*: dict. Same dict as given with added keys for URIs if found.


### **export_uri** *(self, local, fileid='URIs')*<a id="export_uri"></a>

Export URIs from local metadata dicts in {\<album name: {\<title\>: \<URI\>}} format.

> *Parameters*
> - local: dict. Metadata in form {\<name\>: \<list of dicts of metadata incl. path, album, and URI\>}
> - filename: str, default='URIs'. Filename of file to export to in data path.


### **save_json** *(self, file, fileid='data')*<a id="save_json"></a>

Save dict to json file in data path.

> *Parameters*
> - file: dict. Data to save.
> - filename: str, default='data'. Filename to save under.


### **load_json** *(self, filename)*<a id="load_json"></a>

Load json from data path.

> *Parameters*
> - filename: str. Filename to load from.


### **uri_as_key** *(local)*<a id="uri_as_key"></a>

Convert dict from {\<name\>: \<list of dicts of metadata\>} to {\<song URI\>: \<song metadata\>}.

> *Parameters*
> - local: dict. Metadata in form {\<name\>: \<list of dicts of metadata\>}

> *Return*: dict. {\<song URI\>: \<song metadata\>}


### **missing_tags** *(local, tags=None, kind='uri', ignore=None)*<a id="no_images"></a>

Returns lists of dicts of song metadata for songs with missing tags.

> *Parameters*
> - local: dict. Metadata in form <URI>: <dict of metadata>
> - tags: list, default=None. List of tags to consider missing.
> - kind: str, default='uri'. Kind of dict fed to function through local - <album>: <dict of metadata> OR <URI>: <dict of metadata>
> - ignore: list, default=None. List of albums of playlists to exclude in search.

> *Return*: dict. {\<URI\>: \<metadata of song with missing tags\>} OR {\<album/playlist name\>: \<list of metadata of songs with missing tag\>}


### **update_tags** *(self, local, tags, refresh=False, verbose=True)*<a id="update_tags"></a>

Update file's tags from given dictionary of tags.

> *Parameters*
> - local: dict. Metadata in form {\<URI\>: \<dict of local song metadata\>}
> - tags: dict. Tags to be updated in form {\<URI\>: {\<tag name\>: \<tag value\>}}
> - refresh: bool, default=False. Destructively replace tags in each file.
> - verbose: Persist progress bars if True.

### **rebuild_uri_from_tag** *(self, local, tag='comment')*<a id="rebuild_uri_from_tag"></a>

Rebuild stored URI json file database with URIs tagged in local files. Replaces json file if found.

> *Parameters*
> - local: dict. Metadata in form <name>: <list of dicts of metadata>
> - tag: str, default='comment'. Type of tag containing URI.
> - filename: str, default='URIs'. Filename of file to export to in data path.

> *Return*: dict. {\<item\>: \[{\<filename\>: \<URI\>}\]}

[Back to top](#top)
## *class* **Process**<a id="process"></a>

Methods for processing local data. 
> WARNING: only [extract_images](#extract_images) and [embed_images](#embed_images) have been built for general use. Other methods in this function are very specialised for author's needs. Use with caution or prior modification.

* [extract_images](#extract_images)
* [embed_images](#embed_images)
* [caps](#caps)
* [titlecase_folders](#titlecase_folders)
* [titlecase_files](#titlecase_files)
* [tags_from_filename](#tags_from_filename)

### **extract_images** *(self, metadata, kind='local', folderid='local', dim=True, verbose=True)*<a id="extract_images"></a>

Extract and save all embedded images from local files or Spotify tracks.

> *Parameters*
> - metadata: dict. Dict of metadata for local or Spotify data. Local: {\<name\>: \<list of songs metadata\>}. Spotify: {\<name>: {\<'tracks'\>: \<list of songs metadata\>}}
> - kind: str, default='local'. Type of metadata passed to function, 'local' or 'spotify'
> - foldername: str, default='local'. Name of folder to store images i.e. $DATA_PATH/images/<foldername>
> - dim: bool, default=True. Add dimensions to image filenames on export as suffix in parentheses.
> - verbose: bool, default=True. Persist progress bars if True.


### **embed_images** *(self, local, spotify, replace=False)*<a id="embed_images"></a>

Embed images to local files from linked Spotify URI images.

> *Parameters*
> - local: dict. {\<song URI\>: \<local song metadata\>}.
> - spotify: dict. {\<song URI\>: \<spotify song metadata\>}
> - replace: bool, default=False. Replace locally embedded images if True. Otherwise, only add images to files with no embedded image.


### **caps** *(word)*<a id="caps"></a>

Capitalisation cases for titlecase function.

> *Parameters*
> - word: str. Word to consider.

> *Return*: str. Formatted word.


### **titlecase_folders** *(self, folders)*<a id="titlecase_folders"></a>

Rename folders in title case from given songs metadata. Prompts user to confirm each folder name change.

> *Parameters*
> - folders: dict. In format, {\<folder name\>: \<list of dicts of song metadata\>}


### **titlecase_files** *(self, folders, start=None)*<a id="titlecase_files"></a>

Rename song filename from its tags in title case from given songs metadata.
Replaces filename in format given with two options:
- \<track number\> - \<title\> (if track number detected in filename with leading zeros)
- \<title\>

> *Parameters*
> - folders: dict. In format, {\<folder name\>: \<list of dicts of song metadata\>}
> - start: str, default=None. Start tag renaming from this folder.


### **tags_from_filename** *(self, folders, no_reid=None, start=None)*<a id="tags_from_filename"></a>

Replace tags from filename. Accepts filenames in forms:
- \<year\> - \<title\>
- \<track number\> - \<title\> (track number may include leading zeros)
- \<title\>

Automatically replaces filenames with only case-sensitive modifications, or track number changes.
Otherwise, prompts user to confirm changes before modification.

> *Parameters*
> - folders: dict. In format, {\<folder name\>: \<list of dicts of song metadata\>}
> - no_rename: list, default=None. Folders to skip.
> - start: str, default=None. Start tag renaming from this folder.


[Back to top](#top)
## *class* **Spotify** *(Authorise, Endpoints, Search)*<a id="spotify"></a>

Methods for processing Spotify API data.

* [get_playlists_metadata](#get_playlists_metadata)
* [get_tracks_metadata](#get_tracks_metadata)
* [extract_track_metadata](#extract_track_metadata)
* [update_uris](#update_uris)
* [update_playlist](#update_playlist)
* [get_differences](#get_differences)
* [check_uris_on_spotify](#check_uris_on_spotify)

### **get_playlists_metadata** *(self, authorisation, in_playlists=None, verbose=True)*<a id="get_playlists_metadata"></a>

Get metadata from all current user's playlists on Spotify.

> *Parameters*
> - authorisation: dict. Headers for authorisation.
> - in_playlists: list or dict, default=None. Names of playlists to get metadata from.
> - verbose: bool, default=True. Persist progress bars if True.

> *Return*: dict. Spotify playlists in form {\<playlist name>: {dict containing <url> and <tracks> (list of tracks metadata)}}


### **get_tracks_metadata** *(self, uri_list, authorisation, verbose=True)*<a id="get_tracks_metadata"></a>

Get metadata from list of given URIs

> *Parameters*
> - uri_list: list. List of URIs to get metadata for.
> - authorisation: dict. Headers for authorisation.
> - verbose: bool, default=True. Persist progress bars if True.

> *Return*: dict. {\<song URI\>: \<song metadata\>}


### **extract_track_metadata** *(track, position=None, add_features=True)*<a id="extract_track_metadata"></a>

Extract metadata for a given track from spotify API results.

> *Parameters*
> - track: dict. Response from Spotify API.
> - position: int, default=None. Add position of track in playlist to returned metadata.
> - add_features: bool, default=True. Add extra information on audio features.

> *Return*: dict. Metadata dict: position, title, artist, album, track, year, length, image_url, image_height, URI, BPM, song key, time_signature, AUDIO_FEATURES.


### **update_uris** *(self, local, spotify, verbose=True)*<a id="update_uris"></a>

Check and update locally stored URIs for given playlists against respective Spotify playlist's URIs.

> *Parameters*
> - local: dict. Local playlists in form {\<playlist name\>: \<list of track's metadata\>} (incl. URIs)
> - spotify: dict. Spotify playlists in form {\<playlist name>: {dict containing <url> and <tracks> (list of tracks metadata incl. URIs)}
> - verbose: bool, default=True. Print extra info on playlists if True.
> *Return*: dict. Metadata for updated tracks including old and new URIs.


### **update_playlist** *(self, local, spotify, authorisation, verbose=True)*<a id="update_playlist"></a>

Takes dict of local m3u playlists with URIs as keys for each song, adding to or creating Spotify playlists.

> *Parameters*
> - local: dict. Local playlists in form {\<playlist name\>: \<list of track's metadata\>} (incl. URIs)
> - spotify: dict. Spotify playlists in form {\<playlist name>: {dict containing <url> and <tracks> (list of tracks metadata incl. URIs)}
> - authorisation: dict. Headers for authorisation.
> - verbose: bool, default=True. Print extra info on playlists and persist progress bars if True.

> *Return*: bool. False if len(m3u) == 0, True if updated.


### **get_differences** *(local, spotify, verbose=True)*<a id="get_differences"></a>

Produces a report on the differences between local m3u and spotify playlists.

> *Parameters*
> - local: dict. Local playlists in form {\<playlist name\>: \<list of track's metadata\>} (incl. URIs)
> - spotify: dict. Spotify playlists in form {\<playlist name>: {dict containing <url> and <tracks> (list of tracks metadata incl. URIs)}
> - verbose: bool, default=True. Print extra info on differences if True.

> *Return*: 2x dict. Metadata on extra and missing songs.


### **check_uris_on_spotify** *(self, playlists, authorisation, uri_file=None, pause=10, verbose=True)*<a id="check_uris_on_spotify"></a>

Creates temporary playlists from locally stored URIs to check songs have an appropriate URI attached.
User can then manually modify incorrectly associated URIs via the URIs stored in json format.

> *Parameters*
> - playlists: dict. Local playlists in form {\<playlist name\>: \<list of track's metadata> (incl. URIs)}
> - authorisation: dict. Headers for authorisation.
> - uri_file: str, default=None. If defined will automatically open this file from inside data path.
> - pause: int, default=10. Number of temporary playlists to create before pausing to allow user to check.
> - verbose: bool, default=True. Print extra info on playlists and persist progress bars if True.


[Back to top](#top)
## *class* **Search**<a id="search"></a>

Algorithms for associating local files with URIs.

* [search_all](#search_all)
* [get_track_match](#get_track_match)
* [get_album_match](#get_album_match)
* [clean_tags](#clean_tags)
* [quick_match](#quick_match)
* [deep_match](#deep_match)

### **search_all** *(self, playlists, authorisation, kind='playlists', add_back=False, verbose=True, algo=4)*<a id="search_all"></a>

Searches all given local playlists.

> *Parameters*
> - playlists: dict. Dict of {\<name\>: \<list of track metadata\>} for local files to search for.
> - authorisation: dict. Headers for authorisation.
> - kind: str, default='playlists'. Perform searches per track for 'playlists', or as one album for 'album'.
> - add_back: bool, default=False. Add back tracks which already have URIs on input. False returns only search results.
> - verbose: bool, default=True. Print extra information on function running.
> - algo: int, default=4. Algorithm type to use for judging accurate matches. Not used for album queries.
	Search algorithms initially query <title> <artist>. 
	If no results, queries <title> <album>. If no results, queries <title> only.
	Then judges matches based on the following criteria.
		0 = Returns the first result every time.
		1 = Within 15s length and 66% of album names match.
		2 = If no matches from 1, use <title> query. Match within 30s length and 80% of album names match.
		3 = If no matches from 2, use best query. Match closest length with <title> and <artist> match within 66%.
		4 = If no matches from 3, use <title> query. Match closest length with <title> and <artist> match within 80%.
		5 = If no matches from 4, return the first result.

		-1 = Match with algo 3 first.
		-2 = If no matches, match with algo 4.
		-3 = If no matches, match with algo 1.
		-4 = If no matches, match with algo 2.
		-5 = If no matches, return the first result.

> *Returns*
> - results: dict. Results in {\<name\>: \<list of track metadata\>} like input.
> - not_found: dict. Tracks not found in {\<name\>: \<list of track metadata\>} like input.
> - searched: bool. If search has happened, returns True, else False.


### **get_track_match** *(self, song, authorisation, algo=4)*<a id="get_track_match"></a>

Get match for given track.

> *Parameters*
> - song: dict. Metadata for locally stored song.
> - authorisation: dict. Headers for authorisation.
> - algo: int, default=4. Algorithm to use for searching. Refer to search_all method documentation.

> *Return*: dict. Metadata for locally stored song with added matched URI if found.


### **get_album_match** *(self, songs, authorisation, title_len_match=0.6)*<a id="get_album_match"></a>

Get match for given album.

> *Parameters*
> - songs: list. List of dicts of metadata for locally stored songs.
> - authorisation: dict. Headers for authorisation.
> - title_len_match: float, default=0.6. Percentage of words in title to consider a match

> *Return*: list. List of dicts of metadata for locally stored album with added matched URIs if found.


### **clean_tags** *(song)*<a id="clean_tags"></a>

Clean tags for better searching/matching.

> *Parameters*
> - song: dict. Metadata for locally stored song.

> *Return*: title, artist, album cleaned tags


### **quick_match** *(self, song, tracks, algo=4)*<a id="quick_match"></a>

Perform quick match for a given song and its results.

> *Parameters*
> - song: dict. Metadata for locally stored song.
> - tracks: list. Results from Spotify API for given song.
> - algo: int, default=4. Algorithm to use for searching. Refer to search_all method documentation.

> *Return*: dict. Metadata for locally stored song with added matched URI if found. None if not found.


### **deep_match** *(self, song, tracks, title, artist, algo=4)*<a id="deep_match"></a>

Perform deeper match for a given song and its results.

> *Parameters*
> - song: dict. Metadata for locally stored song.
> - tracks: list. Results from Spotify API for given song.
> - title: str. Cleaned title for given song.
> - artist: str. Cleaned artist for given song.
> - algo: int, default=4. Algorithm to use for searching. Refer to search_all method documentation.

> *Return*: dict. Metadata for locally stored song with added matched URI if found. None if not found.


[Back to top](#top)
## *class* **Endpoints**<a id="endpoints"></a>

Methods with useful endpoints from the Spotify API in use by this package.

* [convert](#convert)
* [get_request](#get_request)
* [search](#search)
* [get_user](#get_user)
* [get_tracks](#get_tracks)
* [get_all_playlists](#get_all_playlists)
* [get_playlist_tracks](#get_playlist_tracks)
* [create_playlist](#create_playlist)
* [delete_playlist](#delete_playlist)
* [clear_playlist](#clear_playlist)
* [add_to_playlist](#add_to_playlist)
* [uri_from_link](#uri_from_link)

### **convert** *(self, string, get='id', kind=None)*<a id="convert"></a>

Converts id to required format - api/user URL, URI, or ID

> *Parameters*
> - string: str. URL/URI/ID to convert.
> - get: str, default='id'. Type of string to return. Can be 'open', 'api', 'uri', 'id'.
> - kind: str, default=None. ID type if given string is ID. Examples: 'album', 'playlist', 'track', 'artist'. Refer to Spotify API for other types.

> *Return*: str. Formatted string


### **get_request** *(url, authorisation)*<a id="get_request"></a>

Simple get request for given url

> *Parameters*
> - url: str. URL to send get request.
> - authorisation: dict. Headers for authorisation.
> *Return*: dict. JSON response.


### **search** *(self, query, kind, authorisation)*<a id="search"></a>

Query end point, modify result types return with kind parameter

> *Parameters*
> - query: str. Search query.
> - kind: str, default=None. Examples: 'album', 'track', 'artist'. Refer to Spotify API for other types.
> - authorisation: dict. Headers for authorisation.
> *Return*: dict. JSON response.


### **get_user** *(self, authorisation, user='self')*<a id="get_user"></a>

Get information on given or current user

> *Parameters*
> - authorisation: dict. Headers for authorisation.
> - user: str, default='self'. User ID to get, 'self' uses currently authorised user.
> *Return*: dict. JSON response.


### **get_tracks** *(self, track_list, authorisation, limit=50, verbose=False)*<a id="get_tracks"></a>

Get information for given list of tracks

> *Parameters*
> - track_list: list. List of tracks to get. URL/URI/ID formats accepted.
> - authorisation: dict. Headers for authorisation.
> - limit: int, default=50. Size of batches to request.
> - verbose: bool, default=True. Persist progress bars if True.
> *Return*: list. List of information received for each track.


### **get_all_playlists** *(self, authorisation, names=None, user='self', verbose=False)*<a id="get_all_playlists"></a>

Get all information on all tracks for all given user's playlists

> *Parameters*
> - authorisation: dict. Headers for authorisation.
> - names: list, default=None. Return only these named playlists.
> - user: str, default='self'. User ID to get, 'self' uses currently authorised user.
> - verbose: bool, default=True. Print extra information on function running.
> *Return*: dict. {\<playlist name\>: \<dict of playlist url and response for tracks in playlist\>}


### **get_playlist_tracks** *(self, playlist, authorisation)*<a id="get_playlist_tracks"></a>

Get all tracks from a given playlist.

> *Parameters*
> - playlist: str. Playlist URL/URI/ID to get.
> - authorisation: dict. Headers for authorisation.
> *Return*: list. List of API information received for each track in playlist.


### **create_playlist** *(self, playlist_name, authorisation, give='url')*<a id="create_playlist"></a>

Create an empty playlist for the current user.

> *Parameters*
> - playlist_name. str. Name of playlist to create.
> - authorisation: dict. Headers for authorisation.
> - give: str, default='url'. Convert link to generated playlist to this given type.

> *Return*: str. Link as defined above.


### **delete_playlist** *(self, playlist, authorisation)*<a id="delete_playlist"></a>

Unfollow a given playlist.

> *Parameters*
> - playlist. str. Name of playlist to unfollow.
> - authorisation: dict. Headers for authorisation.

> *Return*: str. HTML response.


### **clear_playlist** *(self, playlist, authorisation, limit=100)*<a id="clear_playlist"></a>

Clear all songs from a given playlist.

> *Parameters*
> - playlist: str/dict. Playlist URL/URI/ID to clear OR dict of metadata with keys 'url' and 'tracks'.
> - authorisation: dict. Headers for authorisation.
> - limit: int, default=100. Size of batches to clear at once, max=100.

> *Return*: str. HTML response.


### **add_to_playlist** *(self, playlist, track_list, authorisation, limit=50, skip_dupes=True)*<a id="add_to_playlist"></a>

Add list of tracks to a given playlist.

> *Parameters*
> - playlist: str. Playlist URL/URI/ID to add to.
> - track_list: list. List of tracks to add. URL/URI/ID formats accepted.
> - authorisation: dict. Headers for authorisation.
> - limit: int, default=50. Size of batches to add.
> - skip_dupes: bool, default=True. Skip duplicates.


### **uri_from_link** *(self, authorisation, link=None)*<a id="uri_from_link"></a>

Returns tracks from a given link in "<track> - <title>": "<URI>" format for a given link.
Useful for manual entry of URIs into stored .json file.

> *Parameters*
> - authorisation: dict. Headers for authorisation.
> - link: str, default=None. Link to print information for. Tested on 'album' and 'playlist' types only.


[Back to top](#top)
## *class* **Authorise**<a id="authorise"></a>

Methods to authorise a user with the Spotify API.

* [auth](#auth)
* [refresh_token](#refresh_token)
* [get_token_user](#get_token_user)
* [get_token_basic](#get_token_basic)
* [load_spotify_token](#load_spotify_token)
* [save_spotify_token](#save_spotify_token)

### **auth** *(self, kind='user', scopes=None, force=False, lines=True, verbose=True)*<a id="auth"></a>

Main method for authentication, tests/refreshes/reauthorises as needed

> *Parameters*
> - kind: str, default='user'. 'user' or 'basic' authorisation.
> - scopes: list, default=None. List of scopes to authorise for user. If None, uses defaults.
> - force: bool, default=False. Ignore stored token and reauthorise new user or basic access token.
> - lines: bool, default=True. Print lines around verbose.
> - verbose: bool, default=True. Print extra information on function running.

> *Return*: dict. Headers for requests authorisation.


### **refresh_token** *(self, verbose=True)*<a id="refresh_token"></a>

Refreshes token once it has expired

> *Parameters*
> - verbose: bool, default=True. Print extra information on function running.

> *Return*: dict. Authorisation response.


### **get_token_user** *(self, scopes=None, verbose=True)*<a id="get_token_user"></a>

Authenticates access to API with given user scopes

> *Parameters*
> - scopes: list, default=None. List of scopes to authorise for user. If None, uses defaults.
> - verbose: bool, default=True. Print extra information on function running.

> *Return*: dict. Authorisation response.


### **get_token_basic** *(self, verbose=True)*<a id="get_token_basic"></a>

Authenticates for basic API access, no user authorisation required

> *Parameters*
> - verbose: bool, default=True. Print extra information on function running.

> *Return*: dict. Authorisation response.


### **load_spotify_token** *(self, verbose=True)*<a id="load_spotify_token"></a>

Load stored spotify token from data folder

> *Parameters*
> - verbose: bool, default=True. Print extra information on function running.

> *Return*: dict. Access token.


### **save_spotify_token** *(self)*<a id="save_spotify_token"></a>
Save new/updated token

[Back to top](#top)