import os
import sys

from m3u2spotify.data import Data
from m3u2spotify.spotify import Spotify

class Main(Data, Spotify):

    def __init__(self, verbose=False):
        env_name = None
        for file in os.listdir():
            if 'secret' in file or '.env' in file:
                env_name = file
                break

        if env_name is None:
            exit('Secrets file not found.')

        Data.__init__(self)
        Spotify.__init__(self, env_name)
        self.verbose = verbose
        self.URI_filename = 'URIs'
        print()

    def auth(self):
        print('\n', '-' * 88, '\n', sep='')

        token = self.load_spotify_token()
        if token is None:
            token = self.auth_user()
        headers, token = self.get_headers(token)
        self.save_spotify_token(token)

        self.headers = headers
        print('\n', '-' * 88, '\n', sep='')
        return headers

    def load_m3u(self):
        m3u = self.get_m3u_metadata(os.environ['PLAYLIST_FOLDER'], self.verbose)
        self.save_json(m3u, 'm3u_metadata')
        m3u = self.import_uri(m3u, self.URI_filename)

        return m3u
    
    def load_spotify(self):
        names = [os.path.splitext(playlist)[0] for playlist in os.listdir(os.environ['PLAYLIST_FOLDER'])]
        spotify = self.get_spotify_metadata(names, self.headers, self.verbose)
        if self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        return spotify

    def uri_update(self, m3u, spotify):
        uris = self.update_uris(m3u, spotify, self.verbose)
        self.save_json(uris, 'URIs_updated')
        self.export_uri(uris, self.URI_filename)
        print('\n', '-' * 88, '\n', sep='')

    def search_update(self, m3u, spotify):
        added, not_found, searched = self.search_all(m3u, self.headers, self.verbose)
        if searched and self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        updated = self.update_playlist(added, spotify, self.headers, self.verbose)
        if updated and self.verbose:
            print('\n', '-' * 88, '\n', sep='')

        if searched or updated:
            self.save_json(added, 'search_added')
            self.save_json(not_found, 'search_not_found')
            self.export_uri(added, self.URI_filename)
            print('\n', '-' * 88, '\n', sep='')

    def differences(self, m3u):
        m3u = self.import_uri(m3u)
        extra, missing = self.get_differences(m3u, self.headers)
        self.save_json(extra, 'spotify_extra')
        self.save_json(missing, 'spotify_missing')
        print('\n', '-' * 88, '\n', sep='')

    def update_artwork(self, m3u, spotify, album='downloads'):
        m3u_uri = self.uri_as_key(m3u)
        spotify_uri = self.uri_as_key(spotify)

        if album:
            m3u_filtered = {}
            for uri, song in m3u_uri.items():
                if song['album'].lower().startswith(album):
                    m3u_filtered[uri] = song
        else:
            m3u_filtered = m3u_uri
        
        no_images = self.no_images(m3u_uri)
        self.save_json(no_images, 'no_images')

        m3u_filtered.update(no_images)
        self.embed_images(m3u_filtered, spotify_uri)

if __name__ == "__main__":
    main = Main()

    m3u_pl = main.load_m3u()
    main.auth()
    spotify_pl = main.load_spotify()

    if len(sys.argv) > 1 and sys.argv[1] == 'artwork':
        main.update_artwork(m3u_pl, spotify_pl, album='asdsadasdasdasd')
    else:
        main.uri_update(m3u_pl, spotify_pl)
        main.search_update(m3u_pl, spotify_pl)
        main.differences(m3u_pl)
    
    print()
