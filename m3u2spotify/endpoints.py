import requests
import sys
from tqdm.auto import tqdm
from json import JSONDecodeError

class Endpoints:
    
    def __init__(self,
                 base_api='https://api.spotify.com/v1', 
                 open_url='https://open.spotify.com'):
        self.BASE_API = base_api  # base URL of all Spotify API endpoints
        self.OPEN_URL = open_url
        
        self.user_id = None
    
    def convert(self, string, get='id', kind=None):
        if not string:
            return
        
        url_check = string.split('.')[0]
        uri_check = string.split(':')
        
        if 'open' in url_check or 'api' in url_check:
            url = string.replace('/v1/', '/')
            url = [i for i in url.split('/') if 'http' not in i.lower() and len(i) > 1]
            kind = url[1][:-1] if url[1][-1].lower() == 's' else url[1]
            key = url[2].split('?')[0]
        elif len(uri_check) == 3:
            kind = uri_check[1]
            key = uri_check[2]
        elif kind:
            kind = str(kind)[:-1] if str(kind)[-1].lower() == 's' else str(kind)
            key = string
        else:
            print("ERROR: ID given but ID type not defined via 'kind' parameter")
            return string
        
        if get == 'api':
            return f'{self.BASE_API}/{kind}s/{key}'
        elif get == 'open':
            return f'{self.OPEN_URL}/{kind}/{key}'
        elif get == 'uri':
            return f'spotify:{kind}:{key}'
        else:
            return key
    
    def search(self, query, kind, authorisation):
        url = f'{self.BASE_API}/search'
        params = {'q': query, 'type': kind, 'limit': 10}
        return requests.get(url, params=params, headers=authorisation).json()[f'{kind}s']['items']
    
    def get_user(self, authorisation, user='self'):
        if user == 'self':
            url = f'{self.BASE_API}/me'
        else:
            url = f'{self.BASE_API}/users/{user}'
            
        r = requests.get(url, headers=authorisation).json()
        if user == 'self':
            self.user_id = r['id']
        
        return r
    
    def get_tracks(self, track_list, authorisation, limit=50, verbose=False):
        url = f'{self.BASE_API}/tracks'
        results = []
        
        id_list = [self.convert(track, get='id') for track in track_list if track is not None]
        bar = range(len(id_list) // limit)
        
        if len(id_list) > 50:
            bar = tqdm(bar, desc=f'Getting tracks from Spotify: ', unit='songs', leave=verbose, file=sys.stdout)

        for i in bar:
            id_string = ','.join([track for track in id_list[limit * i: limit * (i + 1)]])
            results.extend(requests.get(url, params={'ids': id_string}, headers=authorisation).json()['tracks'])
            
        return results
    
    def get_all_playlists(self, authorisation, names=None, user='self', verbose=False):
        if user == 'self':
            if self.user_id is None:
                self.get_user(authorisation)
            user = self.user_id
        
        playlist_results = {'next': f'{self.BASE_API}/users/{user}/playlists'}
        playlists = {}

        while playlist_results['next']:
            playlist_results = requests.get(playlist_results['next'],
                                            params={'limit': 50},
                                            headers=authorisation).json()
            playlist_bar = tqdm(playlist_results['items'],
                                desc='Getting Spotify playlist metadata: ',
                                unit='playlists',
                                leave=verbose, file=sys.stdout)
            playlist_bar = playlist_results['items']

            for playlist in playlist_bar:
                name = playlist['name']
                if names and name not in names:
                    continue
                
                playlist_url = playlist['href']
                playlists[name] = {'url': playlist_url, 'tracks': self.get_playlist_tracks(playlist_url, authorisation)}
                
        return playlists

    def get_playlist_tracks(self, playlist, authorisation):
        if not 'api' in playlist.split('.')[0] or 'tracks' not in playlist.split('/')[-1].lower():
            playlist = f"{self.convert(playlist, get='api')}/tracks"
        
        results = {'next': playlist}
        tracks = []

        while results['next']:
            results = requests.get(results['next'], headers=authorisation).json()
            tracks.extend(results['items'])

        return tracks
    
    def create_playlist(self, playlist_name, authorisation, give='url'):
        if self.user_id is None:
            self.get_user(authorisation)
        url = f'{self.BASE_API}/users/{self.user_id}/playlists'
        
        body = {
            "name": playlist_name,
            "description": "Generated using m3u2spotify: https://github.com/jor-mar/m3u2spotify",
            "public": True
        }

        playlist = requests.post(url, json=body, headers=authorisation).json()['href']
        
        if give != 'url':
            return self.convert(playlist, get=give)
        else:
            return playlist
    
    def delete_playlist(self, playlist, authorisation):
        playlist = f"{self.convert(playlist, get='api')}/followers"
        r = requests.delete(playlist, headers=authorisation)
        try:
            return r.json()
        except JSONDecodeError:
            return {'Success': f"Unfollowed {playlist.split('/')[-2]}"}
    
    def add_to_playlist(self, playlist, track_list, authorisation, limit=50, skip_dupes=True):
        if not 'api' in playlist.split('.')[0]:
            playlist = f"{self.convert(playlist, get='api')}/tracks"
        if len(str(track_list[0]).split(':')) != 3:
            track_list = [self.convert(track, get='uri') for track in track_list if track is not None]

        current_tracks = []
        if skip_dupes:
            current_tracks = self.get_playlist_tracks(playlist, authorisation)
            current_tracks = [track['track']['uri'] for track in current_tracks]
        
        for i in range(len(track_list) // limit + 1):
            tracks = track_list[limit * i: limit * (i + 1)]
            uri_string = ','.join([track for track in tracks if track not in current_tracks])
            requests.post(playlist, params={'uris': uri_string}, headers=authorisation)