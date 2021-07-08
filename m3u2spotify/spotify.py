import os
import re
import sys
import urllib.parse as urlparse
import webbrowser
from os.path import dirname, join

import requests
from dotenv import load_dotenv
from tqdm.auto import tqdm


class Spotify:

    def __init__(self, env_name='.env'):
        ENV_PATH = join(dirname(dirname(__file__)), env_name)
        load_dotenv(ENV_PATH)

        self.CLIENT_ID = os.environ['CLIENT_ID']
        self.CLIENT_SECRET = os.environ['CLIENT_SECRET']

        self.API_URL = 'https://api.spotify.com/v1'  # base URL of all Spotify API endpoints
        self.AUTH_URL = 'https://accounts.spotify.com'  # base URL of all Spotify authorisation
        self.USERAUTH_URL = f'{self.AUTH_URL}/authorize/'  # user authorisations
        self.TOKEN_URL = f'{self.AUTH_URL}/api/token'  # URL for getting spotify tokens
        self.SEARCH_URL = f'{self.API_URL}/search/'
        self.TRACK_URL = f'{self.API_URL}/tracks'
        self.PLAYLIST_URL = f'{self.API_URL}/playlists'

    def auth_basic(self):
        print('Authorising basic API access...', end=' ', flush=True)
        auth_response = requests.post(self.TOKEN_URL, {
            'grant_type': 'client_credentials',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        print('\33[92m', 'Done', '\33[0m', sep='')
        return auth_response

    def auth_user(self):
        print('Authorising user privilege access...')
        params = {'client_id': os.environ['CLIENT_ID'],
                  'response_type': 'code',
                  'redirect_uri': 'http://localhost/',
                  'state': 'm3u2spotify',
                  'scope': 'playlist-modify-public playlist-modify-private'}

        webbrowser.open(requests.post(self.USERAUTH_URL, params=params).url)
        redirect_url = input('Authorise in new tab and input the returned url: ')
        code = urlparse.urlparse(redirect_url).query.split('&')[0].split('=')[1]

        auth_response = requests.post(self.TOKEN_URL, {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost/',
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        print('\33[92m', 'Done', '\33[0m', sep='')

        return auth_response

    def refresh_token(self, token):
        print('Refreshing access token...', end=' ', flush=True)
        auth_response = requests.post(self.TOKEN_URL, {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token'],
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
        }).json()

        if 'refresh_token' not in auth_response:
            auth_response['refresh_token'] = token['refresh_token']

        print('\33[92m', 'Done', '\33[0m', sep='')
        return auth_response

    def get_headers(self, token):
        if not token:
            return

        headers = {'Authorization': f"{token['token_type']} {token['access_token']}"}

        if 'error' in requests.get(f'{self.API_URL}/me', headers=headers).json():
            token = self.refresh_token(token)
            headers = {'Authorization': f"{token['token_type']} {token['access_token']}"}

        return headers, token

    def get_playlists_metadata(self, playlist_names, authorisation, verbose=True):
        playlist_results = {'next': f'{self.API_URL}/me/playlists'}
        playlists = {}

        while playlist_results['next']:
            playlist_results = requests.get(playlist_results['next'],
                                            params={'limit': 50},
                                            headers=authorisation).json()
            playlist_bar = tqdm(playlist_results['items'],
                                desc='Getting Spotify playlist metadata: ',
                                unit='playlists',
                                leave=verbose, file=sys.stdout)

            for playlist in playlist_bar:
                name = playlist['name']

                if name in playlist_names:
                    playlist_url = playlist['tracks']['href']
                    playlists[name] = {'url': playlist_url, 'tracks': []}
                    results = {'next': playlist_url}

                    while results['next']:
                        results = requests.get(results['next'], headers=authorisation).json()
                        tracks = [self.extract_track_metadata(result['track'], i)
                                  for i, result in enumerate(results['items'])]
                        playlists[name]['tracks'].extend(tracks)
        if verbose:
            print('Found the following playlists:')
            max_width = len(max(playlists.keys(), key=len))

            for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
                length = str(len(playlist['tracks'])) + ' tracks'
                print(f'{name : <{max_width}}', ':', '\33[92m', f'{length : >9} ', '\33[0m', sep='')

        return playlists

    def get_tracks_metadata(self, uri_list, authorisation, limit=50, verbose=True):
        metadata = []
        bar = range(len(uri_list) // limit + 1)

        if len(uri_list) > 50:
            bar = tqdm(bar, desc=f'Getting Spotify metadata: ', unit='songs', leave=verbose, file=sys.stdout)

        for i in bar:
            id_string = ','.join(uri.replace('spotify:track:', '')
                                 for uri in uri_list[limit * i: limit * (i + 1)]
                                 if isinstance(uri, str))
            results = requests.get(self.TRACK_URL, params={'ids': id_string}, headers=authorisation).json()['tracks']
            metadata.extend([self.extract_track_metadata(result) for result in results])

        return metadata

    @staticmethod
    def extract_track_metadata(track, position=None):
        image_url = None
        max_height = 0
        for image in track['album']['images']:
            if image['height'] > max_height:
                image_url = image['url']
                max_height = image['height']

        song = {'position': position,
                'title': track['name'],
                'artist': ' '.join(artist['name'] for artist in track['artists']),
                'album': track['album']['name'],
                'track': int(track['track_number']),
                'year': int(re.sub('[^0-9]', '', track['album']['release_date'])[:4]),
                'length': track['duration_ms'] / 1000,
                'image': image_url,
                'image_height': max_height,
                'uri': track['uri']}
        return song

    def update_uris(self, m3u, spotify, verbose=True):
        max_width = len(max(spotify.keys(), key=len))
        updated_uris = {}
        for name, songs in m3u.items():
            if name in spotify:
                i = 0
                if verbose:
                    text = f'Attempting to find URIs in Spotify playlist: {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                spotify_uris = [*[track['uri'] for track in spotify[name]['tracks']], None]
                m3u_uris = [song['uri'] for song in songs if 'uri' in song]
                for song in songs:
                    if 'uri' in song and song.get('uri', None) not in spotify_uris:
                        title, _, _ = self.clean_tags(song)

                        for track in spotify[name]['tracks']:
                            track_title, _, _ = self.clean_tags(track)
                            title_match = all([word in track_title for word in title.split(' ')])

                            if title_match and track['uri'] not in m3u_uris:
                                i += 1
                                updated_uris[name] = updated_uris.get(name, [])
                                song['old_uri'] = song['uri']
                                song['uri'] = track['uri']
                                updated_uris[name].append(song)
                                break
                if verbose:
                    print('\33[92m', f'Done. Updated {i + 1} URIs', '\33[0m', sep='')
        return {'updated': updated_uris}

    def update_playlist(self, m3u, spotify, authorisation, limit=50, verbose=True):
        if len(m3u) == 0:
            return False

        user_id = requests.get(f'{self.API_URL}/me', headers=authorisation).json()['id']
        max_width = len(max(spotify.keys(), key=len))

        playlist_bar = tqdm(reversed(m3u.items()),
                            desc='Adding to Spotify: ',
                            unit='playlists',
                            leave=verbose,
                            total=len(m3u),
                            file=sys.stdout)

        for name, songs in playlist_bar:
            if name in spotify:
                if verbose:
                    text = f'Updating {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                url = spotify[name]['url']
                spotify_uris = [*[track['uri'] for track in spotify[name]['tracks']], None]
                uri_list = [song['uri'] for song in songs if
                            'uri' in song and song.get('uri', None) not in spotify_uris]
            else:
                if verbose:
                    text = f'Creating {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                url = self.create_playlist(name, user_id, authorisation)
                uri_list = [song['uri'] for song in songs if 'uri' in song and song.get('uri', None)]

            for i in range(len(uri_list) // limit + 1):
                uri_string = ','.join(uri_list[limit * i: limit * (i + 1)])
                requests.post(url, params={'uris': uri_string}, headers=authorisation)

            if verbose:
                print('\33[92m', f'Done. Added {len(uri_list)} songs', '\33[0m', sep='')

        return True

    def create_playlist(self, playlist_name, user_id, authorisation):
        body = {
            "name": playlist_name,
            "description": "Generated using m3u2spotify: https://github.com/jor-mar/m3u2spotify",
            "public": True
        }

        playlist = requests.post(f'{self.API_URL}/users/{user_id}/playlists', json=body, headers=authorisation).json()
        return playlist['tracks']['href']

    def search_all(self, playlists, authorisation, kind='playlists', add_back=False, verbose=True):
        results = {}
        not_found = {}
        searched = False

        playlist_bar = tqdm(playlists.items(),
                            desc='Searching: ',
                            unit='groups',
                            leave=verbose,
                            file=sys.stdout)

        for name, songs in playlist_bar:
            search_songs = [song for song in songs if 'uri' not in song]
            has_uri = [song for song in songs if 'uri' in song] if add_back else []

            if len(search_songs) == 0:
                if add_back:
                    results[name] = has_uri
                continue

            searched = True
            if len(search_songs) > 50:
                search_songs = tqdm(search_songs, desc=f'{name}: ', unit='songs', leave=verbose, file=sys.stdout)

            if kind == 'playlists':
                results[name] = [self.get_track_match(song, authorisation) for song in search_songs]
            else:
                results[name] = self.get_album_match(search_songs, authorisation)
            not_found[name] = [result for result in results[name] if 'uri' not in result]
            results[name].extend(has_uri)

            for track in not_found[name]:
                track['uri'] = None

            if verbose:
                print('\33[92m', f'{name}: {len(not_found[name])} songs not found', '\33[0m', sep='')

        return results, not_found, searched

    def get_track_match(self, song, authorisation):
        title_clean, artist_clean, album_clean = self.clean_tags(song)
        results = self.search(f'{title_clean} {artist_clean}', 'track', authorisation)

        if len(results) == 0 and album_clean[:9] != 'downloads':
            results = self.search(f'{title_clean} {album_clean}', 'track', authorisation)

        if len(results) == 0:
            results = self.search(title_clean, 'track', authorisation)

        match = self.strong_match(song, results)

        if not match:
            results_title = self.search(title_clean, 'track', authorisation)
            match = self.strong_match(song, results_title)

            if not match:
                match = self.weak_match(song, results, title_clean, artist_clean)

                if not match:
                    self.weak_match(song, results_title, title_clean, artist_clean)

        return song

    def get_album_match(self, songs, authorisation, title_len_match=0.8):
        artist = min(set(song['artist'] for song in songs), key=len)
        _, artist, album = self.clean_tags({'artist': artist, 'album': songs[0]['album']})

        results = self.search(f'{album} {artist}', 'album', authorisation)
        results = sorted(results, key=lambda x: abs(x['total_tracks'] - len(songs)))

        for result in results:
            album_result = requests.get(result['href'], headers=authorisation).json()
            artists = ' '.join([artist['name'] for artist in album_result['artists']])

            album_match = all([word in album_result['name'].lower() for word in album.split(' ')])
            artist_match = all([word in artists.lower() for word in artist.split(' ')])

            if album_match and artist_match:
                for song in songs:
                    if 'uri' in song:
                        continue

                    title = self.clean_tags({'title': song['title']})[0].split(' ')
                    title_min = len(title) * title_len_match
                    title_min = round(title_min + 1 - (title_min - int(title_min)))

                    for track in album_result['tracks']['items']:
                        # time_match = abs(track['duration_ms'] / 1000 - song['length']) <= 20
                        if sum([word in track['name'].lower() for word in title]) >= title_min:
                            song['uri'] = track['uri']
                            break

            if sum(['uri' not in song for song in songs]) == 0:
                break

        songs = [self.get_track_match(song, authorisation) if 'uri' not in song else song for song in songs]

        return songs

    def search(self, query, type, authorisation):
        params = {'q': query, 'type': type, 'limit': 10}
        return requests.get(self.SEARCH_URL, params=params, headers=authorisation).json()[f'{type}s']['items']

    @staticmethod
    def clean_tags(song):
        title = song.get('title', '')
        artist = song.get('artist', '')
        album = song.get('album', '')

        if 'title' in song:
            title = re.sub("[\(\[].*?[\)\]]", "", title).replace('part ', ' ').replace('the ', ' ')
            title = title.lower().replace('featuring', '').split('feat.')[0].split('ft.')[0].split(' / ')[0]
            title = re.sub("[^A-Za-z0-9']+", ' ', title).strip()

        if 'artist' in song:
            artist = re.sub("[\(\[].*?[\)\]]", "", artist).replace('the ', ' ')
            artist = artist.lower().replace(' featuring', '').split(' feat.')[0].split(' ft.')[0]
            artist = artist.split('&')[0].split(' and ')[0].split(' vs')[0]
            artist = re.sub("[^A-Za-z0-9']+", ' ', artist).strip()

        if 'album' in song:
            album = album.split('-')[0].lower().replace('ep', '')
            album = re.sub("[\(\[].*?[\)\]]", "", album).replace('the ', ' ')
            album = re.sub("[^A-Za-z0-9']+", ' ', album).strip()

        return title, artist, album

    def strong_match(self, song, tracks):
        for track in tracks:
            time_match = abs(track['duration_ms'] / 1000 - song['length']) <= 20
            album_match = song['album'].lower() in track['album']['name'].lower()
            year_match = song['year'] == int(re.sub('[^0-9]', '', track['album']['release_date'])[:4])
            not_karaoke = all(word not in track['album']['name'].lower() for word in ['karaoke', 'backing'])

            for artist_ in track['artists']:
                _, artist_name, _ = self.clean_tags({'artist': artist_['name']})
                not_karaoke = not_karaoke and all(word not in artist_ for word in ['karaoke', 'backing'])
                if not not_karaoke:
                    break

            if any([time_match, album_match, year_match]) and not_karaoke:
                song['uri'] = track['uri']
                return song
        return None

    def weak_match(self, song, tracks, title, artist):
        min_length_diff = 600
        for track in tracks:
            track_name, _, _ = self.clean_tags({'title': track['name']})

            title_match = all([word in track_name for word in title.split(' ')])
            artist_match = True
            length_diff = abs(track['duration_ms'] / 1000 - song['length'])
            not_karaoke = all([word not in track['album']['name'].lower() for word in ['karaoke', 'backing']])

            for artist_ in track['artists']:
                _, artist_name, _ = self.clean_tags({'artist': artist_['name']})

                artist_match = all([word in artist_name for word in artist.split(' ')])
                not_karaoke = not_karaoke and all(word not in artist_ for word in ['karaoke', 'backing'])

                if artist_match or not not_karaoke:
                    break

            if all([(artist_match or title_match), length_diff < min_length_diff, not_karaoke]):
                min_length_diff = length_diff
                song['uri'] = track['uri']
        return song.get('uri', None)

    @staticmethod
    def get_differences(local, spotify):
        print('Getting information on differences between local and Spotify...')

        extra = {}
        missing = {}
        extra_len = 0
        missing_len = 0

        for name, songs in local.items():
            local_uris = [song['uri'] for song in songs if 'uri' in song and song['uri']]
            extra_songs = [track for track in spotify[name]['tracks'] if track['uri'] not in local_uris]

            missing_songs = [song for song in songs if not song.get('uri', None)]

            if len(extra_songs) != 0:
                extra[name] = extra_songs
                extra_len += len(extra_songs)

            if len(missing_songs) != 0:
                missing[name] = missing_songs
                missing_len += len(missing_songs)

        text = f'Spotify playlists have {extra_len} extra songs and {missing_len} missing songs'
        print('\33[92m', text, '\33[0m', sep='')

        return extra, missing

    def check_uris_on_spotify(self, playlists, authorisation, uri_file=None, limit=50, verbose=True):
        user_id = requests.get(f'{self.API_URL}/me', headers=authorisation).json()['id']
        playlist_bar = tqdm(playlists.items(),
                            desc='Adding to Spotify: ',
                            unit='playlists',
                            leave=verbose,
                            file=sys.stdout)
        url_list = []
        max_stops = (len(playlists) // 10) + (len(playlists) % 10 > 0)

        if sys.platform == "linux" and uri_file:
            os.system(f'xdg-open {uri_file}')
        elif sys.platform == "darwin" and uri_file:
            os.system(f'open {uri_file}')
        elif sys.platform == "win32" and uri_file:
            os.startfile(uri_file)

        for n, (playlist_name, songs) in enumerate(playlist_bar):
            url = self.create_playlist(playlist_name, user_id, authorisation)
            url_list.append(url)

            uri_list = [song['uri'] for song in songs if 'uri' in song and song.get('uri', None)]

            for i in range(len(uri_list) // limit + 1):
                uri_string = ','.join(uri_list[limit * i: limit * (i + 1)])
                requests.post(url, params={'uris': uri_string}, headers=authorisation)

            if len(url_list) % 10 == 0:
                input(f'Check playlists and hit enter to continue ({((n + 1) // 10)}/{max_stops})')
                for url in url_list:
                    requests.delete(url.replace('tracks', 'followers'), headers=authorisation)
                url_list = []
