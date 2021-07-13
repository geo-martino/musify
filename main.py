import os
import sys
from os.path import join, dirname, exists, normpath

from dotenv import load_dotenv

from syncify.data import Data
from syncify.spotify import Spotify


class SpotifySync(Data, Spotify):

    def __init__(self, base_api=None, base_auth=None, open_url=None,
                 c_id=None, c_secret=None, playlists=None,
                 music_path=None, win_path=None, mac_path=None, lin_path=None,
                 data=None, uri_file=None, token_file=None, verbose=False, auth=True):
        # load stored environment variables
        load_dotenv()

        self.BASE_API = base_api if base_api else os.environ.get('BASE_API')
        self.BASE_AUTH = base_auth if base_auth else os.environ.get('BASE_AUTH')
        self.OPEN_URL = open_url if open_url else os.environ.get('OPEN_URL')

        self.CLIENT_ID = c_id if c_id else os.environ.get('CLIENT_ID')
        self.CLIENT_SECRET = c_secret if c_secret else os.environ.get('CLIENT_SECRET')

        self.OTHER_PATHS = {'win': normpath(os.environ.get('WIN_PATH', '')),
                            'lin': normpath(os.environ.get('LIN_PATH', '')),
                            'mac': normpath(os.environ.get('MAC_PATH', ''))}

        self.OTHER_PATHS = {k: path for k, path in self.OTHER_PATHS.items() if len(path) > 1}

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

        self.PLAYLISTS = playlists if playlists else os.environ.get('PLAYLISTS')
        playlists = normpath(self.PLAYLISTS.replace('\\', '/')).split('/')
        self.PLAYLISTS_PATH = join(self.MUSIC_PATH, *playlists)

        self.DATA_PATH = normpath(data) if data else normpath(os.environ.get('DATA_PATH', ''))
        if self.DATA_PATH == '.':
            self.DATA_PATH = join(dirname(__file__), 'data')
        self.URI_FILENAME = uri_file if uri_file else os.environ.get('URI_FILENAME')
        self.TOKEN = token_file if token_file else os.environ.get('token')

        Data.__init__(self)
        Spotify.__init__(self)

        self.verbose = verbose
        if auth:
            self.headers = self.auth(verbose)

        self.all_metadata = None
        self.m3u_metadata = None
        self.spotify_metadata = None

    def set_env(self, current_state=True, **kwargs):
        if exists('.env'):
            with open('.env', 'r') as file:
                env = {line.rstrip().split('=')[0]: line.rstrip().split('=')[1] for line in file}

        env_vars = ['BASE_API', 'BASE_AUTH', 'OPEN_URL', 'CLIENT_ID', 'CLIENT_SECRET',
                    'PLAYLISTS', 'WIN_PATH', 'MAC_PATH', 'LIN_PATH', 'DATA_PATH', 'URI_FILENAME']
        if current_state:
            env.update({var: getattr(self, var) for var in env_vars if var in self.__dict__ and getattr(self, var)})
        env.update({k: v for k, v in {**kwargs}.items() if k in env_vars})

        save_vars = [f'{var}={env[var]}\n' for var in env_vars if env.get(var)]
        with open('.env', 'w') as file:
            file.writelines(save_vars)

        return {var: env[var] for var in env_vars if var in self.__dict__ and getattr(self, var)}

    def load_all_local(self, ex_playlists=None, ex_folders=None, in_folders=None):
        all_pl = self.get_all_metadata(ex_playlists=ex_playlists, ex_folders=ex_folders,
                                       in_folders=in_folders, verbose=self.verbose)
        self.save_json(all_pl, 'all_metadata')
        self.all_metadata = self.import_uri(all_pl, self.URI_FILENAME)

        return self

    def load_m3u(self, playlists=None):
        m3u = self.get_m3u_metadata(playlists, self.verbose)
        self.save_json(m3u, 'm3u_metadata')
        self.m3u_metadata = self.import_uri(m3u, self.URI_FILENAME)

        return self

    def load_spotify(self, names=None):
        self.headers = self.auth(lines=False, verbose=True)
        if names and 'm3u' in names:
            names = [os.path.splitext(playlist)[0] for playlist in os.listdir(self.PLAYLISTS_PATH)]

        self.spotify_metadata = self.get_playlists_metadata(self.headers, names, self.verbose)
        if self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        return self

    def update_uri_from_spotify_playlists(self):
        if self.m3u_metadata is None:
            self.load_m3u()
        if self.spotify_metadata is None:
            self.load_spotify(names='m3u')

        uris = self.update_uris(self.m3u_metadata, self.spotify_metadata, self.verbose)
        self.save_json(uris, f'{self.URI_FILENAME}_updated')
        self.export_uri(uris, self.URI_FILENAME)
        print('\n', '-' * 88, '\n', sep='')
        return self

    def search_m3u_to_spotify(self, quick_load=False, refresh=False):
        if not quick_load:
            if self.m3u_metadata is None:
                self.load_m3u()
            if self.spotify_metadata is None:
                self.load_spotify(names='m3u')

            if refresh:
                print('Clearing playlists...', end='')
                for name, playlist in self.spotify_metadata.items():
                    self.clear_playlist(playlist, self.headers)
                    self.spotify_metadata[name]['tracks'] = []
                print('\33[92m', f'Done', '\33[0m')

            added, not_found, searched = self.search_all(self.m3u_metadata, self.headers,
                                                         add_back=refresh, verbose=self.verbose)
            if searched and self.verbose:
                print('\n', '-' * 88, '\n', sep='')
        else:
            added = self.load_json('search_found')
            not_found = None

        updated = self.update_playlist(added, self.spotify_metadata, self.headers, self.verbose)
        if updated and self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        if updated or searched:
            self.save_json(added, 'search_added')
            self.save_json(not_found, 'search_not_found')
            self.export_uri(added, self.URI_FILENAME)
            self.load_spotify(names='m3u')
        return self

    def differences(self):
        if self.m3u_metadata is None:
            self.load_m3u()

        m3u = self.import_uri(self.m3u_metadata)
        self.spotify_metadata = self.get_playlists_metadata(self.headers, m3u, self.verbose)
        extra, missing = self.get_differences(m3u, self.spotify_metadata, self.verbose)
        self.save_json(extra, 'spotify_extra')
        self.save_json(missing, 'spotify_missing')
        return self

    def update_artwork(self, album_prefix=None, replace=False, report=True):
        if self.m3u_metadata is None:
            self.load_m3u()

        m3u_uri = self.uri_as_key(self.m3u_metadata)
        spotify = self.get_tracks_metadata(list(m3u_uri.keys()), self.headers, verbose=self.verbose)
        spotify_uri = self.uri_as_key(spotify)

        if album_prefix:
            m3u_filtered = {}
            for uri, song in m3u_uri.items():
                if song['album'].lower().startswith(album_prefix):
                    m3u_filtered[uri] = song
        else:
            m3u_filtered = m3u_uri

        if report:
            no_images = self.no_images(m3u_filtered)
            self.save_json(no_images, 'no_images')
            if replace:
                m3u_filtered = no_images

        self.embed_images(m3u_filtered, spotify_uri, replace=replace)

        return self

    def get_missing_uri(self, ex_playlists=False, quick_load=False, import_uri=True, drop=True, null_folders=None,
                        start_folder=None, add_back=False):
        if quick_load:
            folders = self.load_json('search_found')
        elif self.all_metadata is None:
            folders = self.get_all_metadata(ex_playlists=ex_playlists, verbose=False)
        else:
            folders = self.all_metadata

        if import_uri:
            folders = self.import_uri(folders, self.URI_FILENAME)
            if drop:
                folders = {folder: [track for track in tracks if 'uri' not in track]
                           for folder, tracks in folders.items()}

        if null_folders:
            for folder, tracks in folders.items():
                if folder in null_folders:
                    for track in tracks:
                        track['uri'] = None

        if start_folder:
            for folder in folders.copy():
                if folder == start_folder:
                    break
                del folders[folder]

        self.auth(lines=False, verbose=True)

        if quick_load:
            found = folders
            not_found = self.load_json('search_not_found')
            searched = False
        else:
            found, not_found, searched = self.search_all(folders, self.headers, 'albums', add_back, self.verbose)

        if searched and self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        if searched:
            self.save_json(found, 'search_found')
            self.save_json(not_found, 'search_not_found')

        if not quick_load and (null_folders or searched):
            self.export_uri(found, self.URI_FILENAME)
            print('\n', '-' * 88, '\n', sep='')

        self.check_uris_on_spotify(found, self.headers, self.URI_FILENAME, verbose=self.verbose)

        return self


if __name__ == "__main__":
    main = SpotifySync(verbose=True, auth=False)
    kwargs = {}

    if len(sys.argv) <= 1:
        options = ', '.join(['update', 'artwork', 'check'])
        exit(f'Define run function. Options: {options}')
    elif len(sys.argv) > 2:
        try:
            kwargs = {kwarg.split("=")[0]: eval(kwarg.split("=")[1]) for kwarg in sys.argv[2:]}
        except NameError:
            kwargs = {kwarg.split("=")[0]: kwarg.split("=")[1].split(",") for kwarg in sys.argv[2:]}

    if sys.argv[1] == 'update':
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_uri_from_spotify_playlists(
            **{k: v for k, v in {**kwargs}.items() if k in main.update_uri_from_spotify_playlists.__code__.co_varnames})
        main.search_m3u_to_spotify(refresh=True, **{k: v for k, v in {**kwargs}.items() if
                                                    k in main.search_m3u_to_spotify.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'refresh':
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_uri_from_spotify_playlists(
            **{k: v for k, v in {**kwargs}.items() if k in main.update_uri_from_spotify_playlists.__code__.co_varnames})
        main.search_m3u_to_spotify(refresh=True, **{k: v for k, v in {**kwargs}.items() if
                                                    k in main.search_m3u_to_spotify.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'differences':
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.differences(**{k: v for k, v in {**kwargs}.items() if k in main.differences.__code__.co_varnames})

    elif sys.argv[1] == 'artwork':
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        main.update_artwork(**{k: v for k, v in {**kwargs}.items() if k in main.update_artwork.__code__.co_varnames})

    elif sys.argv[1] == 'no_images':
        m3u = main.load_m3u()
        main.no_images(m3u)

    elif sys.argv[1] == 'extract_local':
        m3u = main.load_all_local()
        main.extract_images(m3u, kind='local', foldername='local',
                            **{k: v for k, v in {**kwargs}.items() if k in main.extract_images.__code__.co_varnames})

    elif sys.argv[1] == 'extract_spotify':
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        spotify = main.load_spotify()
        main.extract_images(spotify, kind='spotify', foldername='spotify',
                            **{k: v for k, v in {**kwargs}.items() if k in main.extract_images.__code__.co_varnames})

    elif sys.argv[1] == 'check':
        main.auth(**{k: v for k, v in {**kwargs}.items() if k in main.auth.__code__.co_varnames})
        null = ['_Covers', '_Piano', 'Backings', 'Backings NSFW', 'Final Fantasy VII - Piano Collections',
                'Final Fantasy X - Piano Collections', 'Final Fantasy X-2 - Piano Collections',
                'Maturity (Instrumentals)', 'Miss Saigon - OLC (Act 1)', 'Miss Saigon - OLC (Act 1)',
                'Muppet Treasure Island', 'Real Ideas', 'Real OLD Ideas', 'Release', 'Remakes', 'Safe', "Safe '20",
                'Safe (Extras)', 'Safe The Second', 'Safe The Second (Extras)', 'Z', 'Resting State']
        main.get_missing_uri(import_uri=True, null_folders=null,
                             **{k: v for k, v in {**kwargs}.items() if k in main.get_missing_uri.__code__.co_varnames})

    elif sys.argv[1] == 'simplecheck':
        URIs = main.load_json(main.URI_FILENAME)
        main.auth(lines=False, verbose=True)
        main.check_uris_on_spotify(URIs, main.headers)

    print()
