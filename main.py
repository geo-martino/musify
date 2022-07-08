import ast
import os
import shutil
import sys
from os.path import join, dirname, exists, normpath, splitext, basename

from dotenv import load_dotenv

from syncify.data import Data
from syncify.spotify import Spotify


class Syncify(Data, Spotify):

    def __init__(self, base_api=None, base_auth=None, open_url=None,
                 c_id=None, c_secret=None, music_path=None, playlists=None, 
                 win_path=None, mac_path=None, lin_path=None,
                 data=None, uri_file=None, token_file=None, verbose=False, auth=True):
        """
        :param base_api: str, default=None. Base link to access Spotify API.
        :param base_auth: str, default=None. Base link to authorise through Spotify API.
        :param open_url: str, default=None. Base link for user facing links to Spotify items.
        :param c_id: str, default=None. ID of developer API access.
        :param c_secret: str, default=None. Secret code for developer API access.
        
        :param music_path: str, default=None. Base path to all music files
        :param playlists: str, default=None. Relative path to folder containing .m3u playlists, must be in music folder.
        :param win_path: str, default=None. Windows specific path to all music files.
        :param mac_path: str, default=None. Mac specific path to all music files.
        :param lin_path: str, default=None. Linux specific path to all music files.
        
        :param data: str, default=None. Path to folder containing json and image files.
        :param uri_file: str, default=None. Filename of URI json file.
        :param token_file: str, default=None. Filename of Spotify access token json file.
        
        :param verbose: bool, default=False. Print extra information and persist progress bars if True.
        :param auth: bool, default=True. Perform initial authorisation on instantiation if True
        """
        
        # load stored environment variables
        load_dotenv()

        # Spotify URLs
        self.BASE_API = base_api if base_api else os.environ.get('BASE_API')
        self.BASE_AUTH = base_auth if base_auth else os.environ.get('BASE_AUTH')
        self.OPEN_URL = open_url if open_url else os.environ.get('OPEN_URL')

        # Developer API access
        self.CLIENT_ID = c_id if c_id else os.environ.get('CLIENT_ID')
        self.CLIENT_SECRET = c_secret if c_secret else os.environ.get('CLIENT_SECRET')

        # Paths for other operating systems
        self.OTHER_PATHS = {'win': normpath(os.environ.get('WIN_PATH', '')),
                            'lin': normpath(os.environ.get('LIN_PATH', '')),
                            'mac': normpath(os.environ.get('MAC_PATH', ''))}
        self.OTHER_PATHS = {k: path for k, path in self.OTHER_PATHS.items() if len(path) > 1}

        # Get this system's associated paths, and store other system's paths
        if sys.platform == "win32":
            music_path = music_path if music_path else win_path
            self.WIN_PATH = normpath(music_path) if music_path else self.OTHER_PATHS.get('win')
            self.MUSIC_PATH = self.WIN_PATH

            self.LIN_PATH = normpath(lin_path) if lin_path else self.OTHER_PATHS.get('lin')
            self.MAC_PATH = normpath(mac_path) if mac_path else self.OTHER_PATHS.get('mac')

            self.OTHER_PATHS = [path for path in [self.LIN_PATH, self.MAC_PATH] if path]
        elif sys.platform == "linux":
            music_path = music_path if music_path else lin_path
            self.LIN_PATH = normpath(music_path) if music_path else self.OTHER_PATHS.get('lin')
            self.MUSIC_PATH = self.LIN_PATH

            self.WIN_PATH = normpath(win_path) if win_path else self.OTHER_PATHS.get('win')
            self.MAC_PATH = normpath(mac_path) if mac_path else self.OTHER_PATHS.get('mac')

            self.OTHER_PATHS = [path for path in [self.WIN_PATH, self.MAC_PATH] if path]
        elif sys.platform == "darwin":
            music_path = music_path if music_path else mac_path
            self.MAC_PATH = normpath(music_path) if music_path else self.OTHER_PATHS.get('mac')
            self.MUSIC_PATH = self.MAC_PATH

            self.WIN_PATH = normpath(win_path) if win_path else self.OTHER_PATHS.get('win')
            self.LIN_PATH = normpath(lin_path) if lin_path else self.OTHER_PATHS.get('lin')

            self.OTHER_PATHS = [path for path in [self.WIN_PATH, self.LIN_PATH] if path]

        # Build full path to playlist folder from this system's music path
        self.PLAYLISTS = playlists if playlists else os.environ.get('PLAYLISTS')
        playlists = normpath(self.PLAYLISTS.replace('\\', '/')).split('/')
        self.PLAYLISTS_PATH = join(self.MUSIC_PATH, *playlists)

        # Path to data folder and names of URI and token files inside
        self.DATA_PATH = normpath(data) if data else normpath(os.environ.get('DATA_PATH', ''))
        if self.DATA_PATH == '.':
            self.DATA_PATH = join(dirname(__file__), 'data')
        if not exists(self.DATA_PATH):
            os.mkdir(self.DATA_PATH)
        
        self.URI_FILENAME = uri_file if uri_file else os.environ.get('URI_FILENAME')
        self.TOKEN_FILENAME = token_file if token_file else os.environ.get('TOKEN_FILENAME')

        # Instantiate objects
        Data.__init__(self)
        Spotify.__init__(self)

        # Define verbosity and authorise if required
        self.verbose = verbose
        if auth:
            self.headers = self.auth(verbose)

        # Metadata placeholders
        self.all_metadata = None
        self.all_spotify_metadata = None
        self.m3u_metadata = None
        self.spotify_metadata = None

    def set_env(self, current_state=True, **kwargs):
        """
        Save settings to default environment variables. Loads any saved variables and updates as appropriate.
        
        :param current_state: bool, default=True. Use current object variables to update.
        :param **kwargs: pass kwargs for variables to update. Overrides current_state if True.
        :return: dict. Dict of the variables saved.
        """
        if exists('.env'):  # load stored environment variables if they exist
            with open('.env', 'r') as file:
                env = {line.rstrip().split('=')[0]: line.rstrip().split('=')[1] for line in file}
        else:
            env = {}
        
        # required keys
        env_vars = ['BASE_API', 'BASE_AUTH', 'OPEN_URL', 'CLIENT_ID', 'CLIENT_SECRET',
                    'PLAYLISTS', 'WIN_PATH', 'MAC_PATH', 'LIN_PATH', 'DATA_PATH', 'URI_FILENAME', 'TOKEN']
        if current_state:  # update variables from current object
            env.update({var: getattr(self, var) for var in env_vars if var in self.__dict__ and getattr(self, var)})
            
        # update with given kwargs
        env.update({k: v for k, v in {**kwargs}.items() if k in env_vars})

        # build line by line strings each variable and write new .env file
        save_vars = [f'{var}={env[var]}\n' for var in env_vars if env.get(var)]
        with open('.env', 'w') as file:
            file.writelines(save_vars)
        
        # return dict of updated variables
        return {var: env[var] for var in env_vars if var in self.__dict__ and getattr(self, var)}

    def load_all_local(self, ex_playlists=None, ex_folders=None, in_folders=None, refresh=False):
        """
        Loads metadata from all local songs to the object, exports this json to the data folder 
        with filename 'all_metadata.json', and imports URIs from user-defined URIs.json file.
        
        :param ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder.
            Excludes every song from playlists in the default playlist path if True. Ignored if None.
        :param ex_folders: list, default=None. Exclude songs in these folders. Ignored if None.
        :param in_folders: list, default=None. Only include songs in these folders. Ignored if None.
        :param refresh: bool, default=False. Overwrite current URIs with those imported from json file.
        :return: self.
        """
        all_pl = self.get_all_metadata(ex_playlists=ex_playlists, ex_folders=ex_folders,
                                       in_folders=in_folders, verbose=self.verbose)
        self.save_json(all_pl, 'all_metadata')
        self.all_metadata = self.import_uri(all_pl, self.URI_FILENAME, refresh)

        return self

    def load_all_spotify(self, ex_playlists=None, ex_folders=None, in_folders=None):
        """
        Checks API authorisation and loads Spotify metadata for all local files to the object.

        :param ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder.
            Excludes every song from playlists in the default playlist path if True. Ignored if None.
        :param ex_folders: list, default=None. Exclude songs in these folders. Ignored if None.
        :param in_folders: list, default=None. Only include songs in these folders. Ignored if None.
        """
        # authorise
        self.headers = self.auth(lines=False, verbose=True)

        # load local metadata
        self.load_all_local(ex_playlists=None, ex_folders=None, in_folders=None)

        # extract uri list and get spotify metadata
        uri_list = [track['uri'] for tracks in self.all_metadata.values() for track in tracks if 'uri' in track]
        self.all_spotify_metadata = self.get_tracks_metadata(uri_list, self.headers, self.verbose)
        self.save_json(self.all_spotify_metadata, 'all_spotify_metadata')

        return self

    def load_m3u(self, in_playlists=None):
        """
        Loads metadata from all local playlists to the object, exports this json to the data folder 
        with filename 'm3u_metadata.json', and imports URIs from user-defined URIs.json file.
        
        :param in_playlists: list, default=None. List of playlist names to include, returns all if None.
        :return: self.
        """
        m3u = self.get_m3u_metadata(in_playlists, self.verbose)
        self.save_json(m3u, 'm3u_metadata')
        self.m3u_metadata = self.import_uri(m3u, self.URI_FILENAME)

        return self

    def load_spotify(self, in_playlists=None):
        """
        Checks API authorisation and loads metadata from all Spotify playlists to the object.
        
        :param in_playlists: str/list, default=None. List of playlist names to include, returns all if None. 
            Only returns matching local playlist names if 'm3u'.
        :return: self.
        """
        # authorise and get required playlists
        self.headers = self.auth(lines=False, verbose=True)
        if in_playlists and 'm3u' in in_playlists:
            in_playlists = [splitext(playlist)[0] for playlist in os.listdir(self.PLAYLISTS_PATH)]

        # get Spotify metadata
        self.spotify_metadata = self.get_playlists_metadata(self.headers, in_playlists, self.verbose)
        if self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        return self

    def update_uri_from_spotify_playlists(self):
        """
        Update URIs for local files from Spotify playlists.
        Loads m3u and Spotify playlists to object if they have not been loaded.
        
        :return: self.
        """
        # load metadata if not yet done
        if self.m3u_metadata is None:
            self.load_m3u()
        if self.spotify_metadata is None:
            self.load_spotify(in_playlists='m3u')

        # update URIs and save json
        uris = self.update_uris(self.m3u_metadata, self.spotify_metadata, self.verbose)
        self.save_json(uris, f'{self.URI_FILENAME}_updated')
        self.export_uri(uris, self.URI_FILENAME)
        print('\n', '-' * 88, '\n', sep='')
        return self

    def search_m3u_to_spotify(self, quick_load=False, refresh=False):
        """
        Search for URIs for local files that don't have one associated, and update Spotify with new URIs.
        Saves json file for found songs ('search_found.json'), songs added to playlists ('search_added.json'),
        and songs that still have no URI ('search_not_found.json').
        Loads m3u and Spotify playlists to object if they have not been loaded.
        
        :param quick_load: bool, default=False. Load last search from 'search_found.json' file
        :param refresh: bool, default=False. Clear Spotify playlists before updating.
        :return: self.
        """
        if not quick_load:
            # load metadata if not yet done
            if self.m3u_metadata is None:
                self.load_m3u()
            if self.spotify_metadata is None:
                self.load_spotify(in_playlists='m3u')
                
            if refresh:  # clear playlists
                print('Clearing playlists...', end='')
                for name, playlist in self.spotify_metadata.items():
                    self.clear_playlist(playlist, self.headers)
                    self.spotify_metadata[name]['tracks'] = []
                print('\33[92m', 'Done', '\33[0m')

            # search for missing URIs
            added, not_found, searched = self.search_all(self.m3u_metadata, self.headers,
                                                         add_back=refresh, verbose=self.verbose)
            
            if searched:  # save json of results
                self.save_json(added, 'search_found')
                if self.verbose:
                    print('\n', '-' * 88, '\n', sep='')
        else:  # load from last search
            added = self.load_json('search_found')
            not_found = None

        # update playlists with new URIs
        updated = self.update_playlist(added, self.spotify_metadata, self.headers, self.verbose)
        if updated and self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        # save json files, update local URIs, update this object's stored Spotify metadata
        if updated or searched:
            self.save_json(added, 'search_added')
            self.save_json(not_found, 'search_not_found')
            self.export_uri(added, self.URI_FILENAME)
        return self

    def differences(self):
        """
        Produces reports on differences between Spotify and local playlists.
        Saves reports for songs on Spotify not found in local playlists 'spotify_extra.json',
        and local songs with missing URIs and therefore not in Spotify playlists 'spotify_missing.json'.
        
        :return: self.
        """
        # load metadata if not yet done
        if self.m3u_metadata is None:
            self.load_m3u()

        # import local URIs, load spotify metadata, get differences
        m3u = self.import_uri(self.m3u_metadata)
        self.spotify_metadata = self.get_playlists_metadata(self.headers, m3u, self.verbose)
        extra, missing = self.get_differences(m3u, self.spotify_metadata, self.verbose)
        
        # save json files
        self.save_json(extra, 'spotify_extra')
        self.save_json(missing, 'spotify_missing')
        return self

    def update_artwork(self, album_prefix=None, replace=False):
        """
        Update locally embedded images with associated URIs' artwork.
        
        :param album_prefix: str, default=None. If defined, only replace artwork for albums that start with this string.
        :param replace: bool, default=False. Replace locally embedded images if True. 
            Otherwise, only add images to files with no embedded image.
        :return: self.
        """
        # load metadata if not yet done
        if self.all_metadata is None:
            self.load_all_local()
        
        # get latest Spotify metadata for local files
        local_uri = self.uri_as_key(self.all_metadata)
        if not replace:
            local_uri = {uri: track for uri, track in local_uri.items() if not track['has_image']}
        spotify_uri = self.get_tracks_metadata(list(local_uri.keys()), self.headers, verbose=self.verbose)

        if album_prefix:  # filter to only albums that start with album_prefix
            if isinstance(album_prefix, list):
                album_prefix = album_prefix[0]
            m3u_filtered = {}
            for uri, song in local_uri.items():
                if song['album'].lower().startswith(album_prefix.lower()):
                    m3u_filtered[uri] = song
        else:  # use all
            m3u_filtered = local_uri

        # embed images and produce report listing which songs have been updated
        self.embed_images(m3u_filtered, spotify_uri, replace=replace)
        self.save_json(m3u_filtered, 'updated_artwork')

        return self

    def get_missing_uri(self, ex_playlists=False, quick_load=False, import_uri=True, drop=True, null_folders=None,
                        start_folder=None, add_back=False, tags=None):
        """
        Search for URIs for files missing them and review through Spotify by means of creating and manually 
        checking temporary playlists.
        
        :param ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder.
            Excludes every song from playlists in the default playlist path if True. Ignored if None.
        :param quick_load: bool, default=False. Load last search from 'search_found.json' file
        :param import_uri: bool, default=True. Import associated URIs for each local song.
        :param drop: bool, default=True. If import_uri is True, remove any song that doesn't have a URI, 
            hence skipping a search for new URIs.
        :param null_folders: list, default=None. Give all songs in these folders the URI value of 'None', hence
            skipping all searches and additions to playlist for these songs. Useful for albums not on Spotify.
        :param start_folder: str, default=None. Start creation of temporary playlists from folder starting with this string.
        :param add_back: bool, default=False. Add back tracks which already have URIs on input. 
            False returns only search results.
        :param tags: list, default=None. List of tags to update for local song metadata.
        :return: self.        
        """
        if quick_load:  # load from last search
            folders = self.load_json('search_found')
        else:
            if self.all_metadata is None:  # load metadata if not yet done
                self.all_metadata = self.get_all_metadata(ex_playlists=ex_playlists, verbose=False)
            folders = self.all_metadata

        if import_uri:  # import locally stored URIs
            folders = self.import_uri(folders, self.URI_FILENAME, refresh=True)
            if drop:  # drop files with no URIs
                folders = {folder: [track for track in tracks if 'uri' in track]
                           for folder, tracks in folders.items()}

        if null_folders:  # set all URIs for songs in these folders to None, effectively blacklisting them
            for folder, tracks in folders.items():
                if folder in null_folders:
                    for track in tracks:
                        track['uri'] = None

        if start_folder:  # remove all folders before start_folder
            for folder in folders.copy():
                if folder.lower().strip().startswith(start_folder):
                    break
                del folders[folder]

        self.auth(lines=False, verbose=True)
        
        if quick_load:  # set variables for quick_load
            found = folders
            not_found = self.load_json('search_not_found')
            searched = False
        else:  # search
            found, not_found, searched = self.search_all(folders, self.headers, 'albums', add_back, self.verbose)

        if searched and self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        if searched:  # save json files
            self.save_json(found, 'search_found')
            self.save_json(not_found, 'search_not_found')

        if not quick_load and (null_folders or searched):  # export URIs if updating has occurred
            self.export_uri(found, self.URI_FILENAME)
            print('\n', '-' * 88, '\n', sep='')

        # begin creation of temporary playlists and check
        self.check_uris_on_spotify(found, self.headers, self.URI_FILENAME, verbose=self.verbose)

        if tags and found:
            # import new uris, get spotify metadata, and update tags of songs
            found = self.import_uri(found, self.URI_FILENAME, refresh=True)
            uri_list = [song['uri'] for songs in found.values() for song in songs]
            spotify_metadata = self.get_tracks_metadata(uri_list, self.headers)
            self.spotify_to_tag(tags, spotify_metadata)

        return self

    def spotify_to_tag(self, tags, metadata=None, reduce=True, refresh=False):
        """
        Updates local file tags with tags from Spotify metadata.
        Tag names for each file extension viewable in self.filetype_tags[FILE_EXT].keys()

        :param tags: list. List of tags to update.
        :param metadata: dict, default=None. Metadata of songs to update in form <URI>: <Spotify metadata>
        :param reduce: bool, default=True. Reduce the list of songs to update to only those with missing tags.
        :param refresh: bool, default=False. Destructively replace tags in each file.
        """
        # load metadata if not yet done
        if self.all_metadata is None:
            self.load_all_local()

        get_tags = {}
        if reduce:
            for folder, songs in self.all_metadata.items():
                for song in songs:
                    if not 'uri' in song:
                        continue
                    if not ('.m4a' in song['path'] and any([t in tags for t in ['bpm', 'key']])):
                        if any([song[tag] is None and song['uri'] for tag in tags if tag in song]):
                            get_tags[song['uri']] = song
        else:
            get_tags = self.uri_as_key(self.all_metadata)
        
        if not get_tags:
            return
        
        self.auth(lines=False, verbose=True)
        metadata = self.get_tracks_metadata(get_tags.keys(), self.headers, verbose=self.verbose)
        
        for uri, track in metadata.items():
            metadata[uri] = {k: v for k, v in track.items() if k in tags}
            if 'uri' in get_tags[uri]:
                metadata[uri]['comment'] = get_tags[uri].pop('uri')

        self.update_tags(get_tags, metadata, refresh, verbose=self.verbose)


if __name__ == "__main__":
    # instantiate main object
    main = Syncify(verbose=True, auth=False)
    kwargs = {}

    options = ', '.join(['update', 'refresh', 'differences', 'artwork', 'missing_artwork', 'missing_tags', 
                        'extract_local', 'extract_spotify', 'check', 'simplecheck', 'update_tags', 'rebuild_uri'])

    if len(sys.argv) <= 1:  # no function given
        exit(f'Define run function. Options: {options}')
    elif sys.argv[1] not in options:  # function name error
        exit(f'Run function not recognised. Options: {options}')
    elif len(sys.argv) > 2:  # extract kwargs
        for kwarg in sys.argv[2:]:
            kw = kwarg.split("=")[0]
            try:
                kwargs[kw] = eval(kwarg.split("=")[1])
            except NameError:
                if len(kwarg.split("=")[1].split(",")) == 1:
                    kwargs[kw] = kwarg.split("=")[1]
                else:
                    kwargs[kw] = kwarg.split("=")[1].split(",")
    
    ### UPDATE NOT CURRENTLY WORKING, USE REFRESH INSTEAD ###
    if sys.argv[1] == 'update':  # run functions for updating Spotify playlists with new songs
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_uri_from_spotify_playlists(
            **{k: v for k, v in {**kwargs}.items() if k in main.update_uri_from_spotify_playlists.__code__.co_varnames})
        main.search_m3u_to_spotify(refresh=False, **{k: v for k, v in {**kwargs}.items() 
                                                     if k in main.search_m3u_to_spotify.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'refresh':  # run functions for clearing and updating Spotify playlists with new songs
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_uri_from_spotify_playlists(
            **{k: v for k, v in {**kwargs}.items() if k in main.update_uri_from_spotify_playlists.__code__.co_varnames})
        main.search_m3u_to_spotify(refresh=True, **{k: v for k, v in {**kwargs}.items() 
                                                    if k in main.search_m3u_to_spotify.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'differences':  # run functions to produce report on differences between local and Spotify
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'artwork':  # run functions to update artwork
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_artwork(**{k: v for k, v in {**kwargs}.items() if k in main.update_artwork.__code__.co_varnames})

    elif sys.argv[1] == 'missing_artwork':  # run functions to produce report on local songs with missing artwork
        main.load_all_local()
        report = main.missing_tags(main.all_metadata, tags=['has_image'], kind='album')
        main.save_json(report, 'missing_artwork')

    elif sys.argv[1] == 'extract_local':  # run functions to extract all embedded images from locally stored songs
        main.load_all_local()
        main.extract_images(main.all_metadata, kind='local', foldername='local',
                            **{k: v for k, v in {**kwargs}.items() if k in main.extract_images.__code__.co_varnames})

    elif sys.argv[1] == 'extract_spotify':  # run functions to extract all artwork from locally listed Spotify URIs
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        spotify = main.load_spotify()
        main.extract_images(spotify, kind='spotify', foldername='spotify',
                            **{k: v for k, v in {**kwargs}.items() if k in main.extract_images.__code__.co_varnames})

    elif sys.argv[1] == 'check':  # run functions to search for and check associated URIs for all local songs
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        null = ['_Covers', '_Piano', 'Backings', 'Backings NSFW', 'Final Fantasy VII - Piano Collections',
                'Final Fantasy X - Piano Collections', 'Final Fantasy X-2 - Piano Collections',
                'Maturity (Instrumentals)', 'Miss Saigon - OLC (Act 1)', 'Miss Saigon - OLC (Act 1)',
                'Muppet Treasure Island', 'Old Ideas', 'Real Ideas', 'Real OLD Ideas', 'Release', 'Remakes', 
                'Safe', "Safe '20", 'Safe (Extras)', 'Safe The Second', 'Safe The Second (Extras)', 'Z', 'Resting State']
        tags = ['bpm', 'key', 'uri'] if 'tags' not in kwargs else kwargs.pop('tags')
        main.get_missing_uri(import_uri=True, null_folders=null, drop=False, tags=tags,
                             **{k: v for k, v in {**kwargs}.items() if k in main.get_missing_uri.__code__.co_varnames})

    elif sys.argv[1] == 'simplecheck':  # run functions to just check all already associated URIs with no search
        URIs = main.load_json(main.URI_FILENAME)
        main.auth(lines=False, verbose=True)
        main.check_uris_on_spotify(URIs, main.headers)

    elif sys.argv[1] == 'missing_tags':  # run functions to produce report on local songs with missing tags
        main.load_all_local()
        tags = ['title', 'artist', 'album', 'track', 'year', 'genre'] if 'tags' not in kwargs else kwargs.pop('tags')
        ignore =  ['Backings', 'Backings NSFW', 'Old Ideas', 'Real Ideas', 'Real OLD Ideas', 'Release', 'Remakes']
        report = main.missing_tags(main.all_metadata, tags=tags, kind='album', ignore=ignore)
        main.save_json(report, 'missing_tags')
    
    elif sys.argv[1] == 'update_tags':
        # main.load_all_spotify()
        tags = ['bpm', 'key', 'uri'] if 'tags' not in kwargs else kwargs.pop('tags')
        main.spotify_to_tag(tags, **{k: v for k, v in {**kwargs}.items() if k in main.spotify_to_tag.__code__.co_varnames})

    elif sys.argv[1] == 'rebuild_uri':
        main.load_all_local()
        json_path = join(main.DATA_PATH, main.URI_FILENAME)
        if exists(json_path + '.json'):
            shutil.copy(json_path + '.json', json_path + '_OLD.json')
        main.rebuild_uri_from_tag(main.all_metadata, 'comment', main.URI_FILENAME)


    print()
