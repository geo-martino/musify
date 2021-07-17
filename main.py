import os
import sys
from os.path import join, dirname, exists, normpath, splitext, basename

from dotenv import load_dotenv

from syncify.data import Data
from syncify.spotify import Spotify


class SpotifySync(Data, Spotify):

    def __init__(self, base_api=None, base_auth=None, open_url=None,
                 c_id=None, c_secret=None, playlists=None,
                 music_path=None, win_path=None, mac_path=None, lin_path=None,
                 data=None, uri_file=None, token_file=None, verbose=False, auth=True):
        """
        :param base_api: str, default=None. Base link to access Spotify API.
        :param base_auth: str, default=None. Base link to authorise through Spotify API.
        :param open_url: str, default=None. Base link for user facing links to Spotify items.
        :param c_id: str, default=None. ID of developer API access.
        :param c_secret: str, default=None. Secret code for developer API access.
        
        :param playlists: str, default=None. Relative path to folder containing .m3u playlists, must be in music folder.
        :param music_path: str, default=None. Base path to all music files
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
        self.URI_FILENAME = uri_file if uri_file else os.environ.get('URI_FILENAME')
        self.TOKEN = token_file if token_file else os.environ.get('token')

        # Instantiate objects
        Data.__init__(self)
        Spotify.__init__(self)

        # Define verbosity and authorise if required
        self.verbose = verbose
        if auth:
            self.headers = self.auth(verbose)

        # Metadata placeholders
        self.all_metadata = None
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
                    'PLAYLISTS', 'WIN_PATH', 'MAC_PATH', 'LIN_PATH', 'DATA_PATH', 'URI_FILENAME']
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

    def load_all_local(self, ex_playlists=None, ex_folders=None, in_folders=None):
        """
        Loads metadata from all local songs to the object, exports this json to the data folder 
        with filename 'all_metadata.json', and imports URIs from user-defined URIs.json file.
        
        :param ex_playlists: list, default=None. Exclude songs with paths listed in playlists in this playlist folder.
            Excludes every song from playlists in the default playlist path if True. Ignored if None.
        :param ex_folders: list, default=None. Exclude songs in these folders. Ignored if None.
        :param in_folders: list, default=None. Only include songs in these folders. Ignored if None.
        :return: self.
        """
        all_pl = self.get_all_metadata(ex_playlists=ex_playlists, ex_folders=ex_folders,
                                       in_folders=in_folders, verbose=self.verbose)
        self.save_json(all_pl, 'all_metadata')
        self.all_metadata = self.import_uri(all_pl, self.URI_FILENAME)

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
        # authorise and get required playlist
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
                    self.clear_playlist(playlist['url'], self.headers)
                    self.spotify_metadata[name]['tracks'] = []
                print('\33[92m', f'Done', '\33[0m')

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
            self.load_spotify(in_playlists='m3u')
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

    def update_artwork(self, album_prefix=None, replace=False, report=True):
        """
        Update locally embedded images with associated URIs' artwork.
        
        :param album_prefix: str, default=None. If defined, only replace artwork for albums that start with this string.
        :param replace: bool, default=False. Replace locally embedded images if True. 
            Otherwise, only add images to files with no embedded image.
        :param report: bool, default=True. Export 'no_images.json' file with information on which files had missing
            images before running the program.
        :return: self.
        """
        # load metadata if not yet done
        if self.m3u_metadata is None:
            self.load_m3u()

        # get latest Spotify metadata for local files and reformat dict to <URI>: <metadata> format for each
        m3u_uri = self.uri_as_key(self.m3u_metadata)
        spotify = self.get_tracks_metadata(list(m3u_uri.keys()), self.headers, verbose=self.verbose)
        spotify_uri = self.uri_as_key(spotify)

        if album_prefix:  # filter to only albums that start with album_prefix
            m3u_filtered = {}
            for uri, song in m3u_uri.items():
                if song['album'].lower().startswith(album_prefix):
                    m3u_filtered[uri] = song
        else:  # use all
            m3u_filtered = m3u_uri

        if report:  # produce report on local songs with missing embedded images
            no_images = self.no_images(m3u_filtered)
            self.save_json(no_images, 'no_images')

        # embed images
        self.embed_images(m3u_filtered, spotify_uri, replace=replace)

        return self

    def get_missing_uri(self, ex_playlists=False, quick_load=False, import_uri=True, drop=True, null_folders=None,
                        start_folder=None, add_back=False):
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
        :param start_folder: str, default=None. Start creation of temporary playlists from this folder.
        :param add_back: bool, default=False. Add back tracks which already have URIs on input. 
            False returns only search results.
        :return: self.        
        """
        if quick_load:  # load from last search
            folders = self.load_json('search_found')
        elif self.all_metadata is None:  # load metadata if not yet done
            folders = self.get_all_metadata(ex_playlists=ex_playlists, verbose=False)
        else:
            folders = self.all_metadata

        if import_uri:  # import locally stored URIs
            folders = self.import_uri(folders, self.URI_FILENAME)
            if drop:  # drop files with no URIs
                folders = {folder: [track for track in tracks if 'uri' not in track]
                           for folder, tracks in folders.items()}

        if null_folders:  # set all URIs for songs in these folders to None, effectively blacklisting them
            for folder, tracks in folders.items():
                if folder in null_folders:
                    for track in tracks:
                        track['uri'] = None

        if start_folder:  # remove all folders before start_folder
            for folder in folders.copy():
                if folder == start_folder:
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

        return self


if __name__ == "__main__":
    # instantiate main object
    main = SpotifySync(verbose=True, auth=False)
    kwargs = {}

    if len(sys.argv) <= 1:  # error, return
        options = ', '.join(['update', 'refresh', 'differences', 'artwork', 'no_images', 
                             'extract_local', 'extract_spotify', 'check', 'simplecheck'])
        exit(f'Define run function. Options: {options}')
    elif len(sys.argv) > 2:  # extract kwargs
        try:
            kwargs = {kwarg.split("=")[0]: eval(kwarg.split("=")[1]) for kwarg in sys.argv[2:]}
        except NameError:
            kwargs = {kwarg.split("=")[0]: kwarg.split("=")[1].split(",") for kwarg in sys.argv[2:]}

    if sys.argv[1] == 'update':  # run functions for updating Spotify playlists with new songs
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_uri_from_spotify_playlists(
            **{k: v for k, v in {**kwargs}.items() if k in main.update_uri_from_spotify_playlists.__code__.co_varnames})
        main.search_m3u_to_spotify(refresh=True, **{k: v for k, v in {**kwargs}.items() if
                                                    k in main.search_m3u_to_spotify.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'refresh':  # run functions for clearing and updating Spotify playlists with new songs
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_uri_from_spotify_playlists(
            **{k: v for k, v in {**kwargs}.items() if k in main.update_uri_from_spotify_playlists.__code__.co_varnames})
        main.search_m3u_to_spotify(refresh=True, **{k: v for k, v in {**kwargs}.items() if
                                                    k in main.search_m3u_to_spotify.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'differences':  # run functions to produce report on differences between local and Spotify
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'artwork':  # run functions to update artwork
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_artwork(**{k: v for k, v in {**kwargs}.items() if k in main.update_artwork.__code__.co_varnames})

    elif sys.argv[1] == 'no_images':  # run functions to produce report on local songs with missing artwork
        m3u = main.load_m3u()
        main.no_images(m3u)

    elif sys.argv[1] == 'extract_local':  # run functions to extract all embedded images from locally stored songs
        m3u = main.load_all_local()
        main.extract_images(m3u, kind='local', foldername='local',
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
                'Muppet Treasure Island', 'Real Ideas', 'Real OLD Ideas', 'Release', 'Remakes', 'Safe', "Safe '20",
                'Safe (Extras)', 'Safe The Second', 'Safe The Second (Extras)', 'Z', 'Resting State']
        main.get_missing_uri(import_uri=True, null_folders=null,
                             **{k: v for k, v in {**kwargs}.items() if k in main.get_missing_uri.__code__.co_varnames})

    elif sys.argv[1] == 'simplecheck':  # run functions to just check all already associated URIs with no search
        URIs = main.load_json(main.URI_FILENAME)
        main.auth(lines=False, verbose=True)
        main.check_uris_on_spotify(URIs, main.headers)

    print()
