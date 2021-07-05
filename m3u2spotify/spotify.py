import os
import re
import urllib.parse as urlparse
import webbrowser
from os.path import dirname, join

import requests
from dotenv import load_dotenv


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
        if token is None:
            return None
        
        headers = {'Authorization': f"{token['token_type']} {token['access_token']}"}

        if 'error' in requests.get(f'{self.API_URL}/me', headers=headers).json():
            token = self.refresh_token(token)
            headers = {'Authorization': f"{token['token_type']} {token['access_token']}"}
            
        return headers, token

    def get_spotify_metadata(self, playlist_names, authorisation, verbose=True):
        if verbose:
            print('Extracting Spotify playlist track information...', end=' ', flush=True)

        playlist_results = {'next': f'{self.API_URL}/me/playlists'}
        playlists = {}

        while playlist_results['next'] is not None:
            playlist_results = requests.get(playlist_results['next'], params={'limit': 50},
                                            headers=authorisation).json()
            for playlist in playlist_results['items']:
                name = playlist['name']

                if name in playlist_names:
                    playlist_url = playlist['tracks']['href']
                    playlists[name] = {'url': playlist_url, 'tracks': []}
                    results = {'next': playlist_url}
                    while results['next'] is not None:
                        results = requests.get(results['next'], headers=authorisation).json()
                        tracks = [self.get_track_metadata(i, result['track']) for i, result in
                                  enumerate(results['items'])]
                        playlists[name]['tracks'].extend(tracks)
        if verbose:
            print('\33[92m', 'Done', '\33[0m', sep='')

            print('Found the following playlists:')
            max_width = len(max(playlists.keys(), key=len))
            for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
                length = str(len(playlist['tracks'])) + ' tracks'
                print(f'{name : <{max_width}}', ':', '\33[92m', f'{length : >9} ', '\33[0m', sep='')

        return playlists

    @staticmethod
    def get_track_metadata(position, track):
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
                        title, _, _ = self.clean_tags(song, 'title')
                        for track in spotify[name]['tracks']:
                            track_title, _, _ = self.clean_tags(track, 'title')
                            title_match = all([word in track_title for word in title.split(' ')])
                            if title_match and track['uri'] not in m3u_uris:
                                i += 1
                                updated_uris[name] = updated_uris.get(name, [])
                                song['old_uri'] = song['uri']
                                song['uri'] = track['uri']
                                updated_uris[name].append(song)
                                break
                if verbose:
                    print('\33[92m', f'Done. Updated {i} URIs.', '\33[0m', sep='')
        return {'updated': updated_uris}

    def update_playlist(self, m3u, spotify, authorisation, limit=50, verbose=True):
        if len(m3u) == 0:
            return False
        
        user_id = requests.get(f'{self.API_URL}/me', headers=authorisation).json()['id']
        max_width = len(max(spotify.keys(), key=len))

        for name, songs in reversed(m3u.items()):
            if name in spotify:
                if verbose:
                    text = f'Updating Spotify playlist: {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                url = spotify[name]['url']
                spotify_uris = [*[track['uri'] for track in spotify[name]['tracks']], None]
                uri_list = [song['uri'] for song in songs if
                            'uri' in song and song.get('uri', None) not in spotify_uris]
            else:
                if verbose:
                    text = f'Creating Spotify playlist: {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                url = self.create_playlist(name, user_id, authorisation)
                uri_list = [song['uri'] for song in songs if 'uri' in song and song.get('uri', None) is not None]

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

    def search_all(self, m3u_playlists, authorisation, verbose=True):
        results = {}
        not_found = {}
        max_width = len(max(m3u_playlists.keys(), key=len)) + len(str(len(max(m3u_playlists.values(), key=len))))
        searched = False

        for name, songs in m3u_playlists.items():
            search_songs = [song for song in songs if 'uri' not in song]
            if len(search_songs) == 0:
                continue
            
            if verbose:
                text = f'Searching for {len(search_songs)} songs from {name}.m3u...'
                print(f"{text : <{len(text) + max_width - len(str(len(search_songs))) - len(name)}}", end=' ', flush=True)

            searched = True
            results[name] = [self.get_uri(song, authorisation) for song in search_songs]
            not_found[name] = [result for result in results[name] if 'uri' not in result]

            for track in not_found[name]:
                track['uri'] = None

            if verbose:
                print('\33[92m', f'Done. {len(not_found[name])} songs not found.', '\33[0m', sep='')

        return results, not_found, searched

    def get_uri(self, song, authorisation):
        title_clean, artist_clean, album_clean = self.clean_tags(song)
        results = self.search(f'{title_clean} {artist_clean}', authorisation)

        if len(results) == 0 and album_clean[:9] != 'downloads':
            results = self.search(f'{title_clean} {album_clean}', authorisation)

        if len(results) == 0:
            results = self.search(title_clean, authorisation)

        match = self.strong_match(song, results)

        if match is None:
            results_title = self.search(title_clean, authorisation)
            match = self.strong_match(song, results_title)

            if match is None:
                match = self.weak_match(song, results, title_clean, artist_clean)

                if match is None:
                    self.weak_match(song, results_title, title_clean, artist_clean)

        return song

    def search(self, query, authorisation):
        params = {'q': query, 'type': 'track', 'limit': 10}
        return requests.get(self.SEARCH_URL, params=params, headers=authorisation).json()['tracks']['items']

    @staticmethod
    def clean_tags(song, tags='all'):
        if 'all' in tags:
            tags = ['title', 'artist', 'album']

        title = song['title']
        artist = song['artist']
        album = song['album']

        if 'title' in tags:
            title = re.sub("[\(\[].*?[\)\]]", "", title).replace('part ', ' ').replace('the ', ' ')
            title = title.lower().replace('featuring', '').split('feat.')[0].split('ft.')[0].split(' / ')[0]
            title = re.sub("[^A-Za-z0-9']+", ' ', title).strip()

        if 'artist' in tags:
            artist = re.sub("[\(\[].*?[\)\]]", "", artist).replace('the ', ' ')
            artist = artist.lower().replace(' featuring', '').split(' feat.')[0].split(' ft.')[0]
            artist = artist.split('&')[0].split(' and ')[0].split(' vs')[0]
            artist = re.sub("[^A-Za-z0-9']+", ' ', artist).strip()

        if 'album' in tags:
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
                d = {'title': '', 'artist': artist_['name'], 'album': ''}
                _, artist_name, _ = self.clean_tags(d, ['title', 'artist'])
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
            d = {'title': track['name'], 'artist': '', 'album': ''}
            track_name, _, _ = self.clean_tags(d, ['title', 'artist'])

            title_match = all([word in track_name for word in title.split(' ')])
            artist_match = True
            length_diff = abs(track['duration_ms'] / 1000 - song['length'])
            not_karaoke = all([word not in track['album']['name'].lower() for word in ['karaoke', 'backing']])

            for artist_ in track['artists']:
                d = {'title': '', 'artist': artist_['name'], 'album': ''}
                _, artist_name, _ = self.clean_tags(d, ['title', 'artist'])

                artist_match = all([word in artist_name for word in artist.split(' ')])
                not_karaoke = not_karaoke and all(word not in artist_ for word in ['karaoke', 'backing'])

                if artist_match or not not_karaoke:
                    break

            if all([(artist_match or title_match), length_diff < min_length_diff, not_karaoke]):
                min_length_diff = length_diff
                song['uri'] = track['uri']
        return song.get('uri', None)

    def get_differences(self, m3u, authorisation):
        print('Getting information on differences between m3u and Spotify...', end=' ', flush=True)

        spotify = self.get_spotify_metadata(m3u, authorisation, verbose=False)
        extra = {}
        missing = {}
        extra_len = 0
        missing_len = 0

        for name, songs in m3u.items():
            m3u_uris = [song['uri'] for song in songs if 'uri' in song and song['uri'] is not None]
            extra_songs = [track for track in spotify[name]['tracks'] if track['uri'] not in m3u_uris]

            missing_songs = [song for song in songs if song.get('uri', None) is None]

            if len(extra_songs) != 0:
                extra[name] = extra_songs
                extra_len += len(extra_songs)
            
            if len(missing_songs) != 0:
                missing[name] = missing_songs
                missing_len += len(missing_songs)

        print('\33[92m', 'Done', '\33[0m', sep='')
        print('\33[92m', f'Spotify playlists have {extra_len} extra songs and {missing_len} missing songs', '\33[0m', sep='')

        return extra, missing
