import sys

import requests
from tqdm.auto import tqdm


class Endpoints:

    def __init__(self):

        # stores currently authorised user id
        self.user_id = None

    def convert(self, string, get='id', kind=None):
        """converts id to required format - api/user URL, URI, or ID"""
        if not string:  # if string is None, skip checks
            return

        # format for URL/URI checks
        url_check = string.split('.')[0]  # url links always start with 'open' or 'api'
        uri_check = string.split(':')  # URIs are always 3 strings separated by :

        # extract id and id types
        if 'open' in url_check or 'api' in url_check:
            # ensure splits give all useful information at the same indices
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

        # reformat
        if get == 'api':
            return f'{self.BASE_API}/{kind}s/{key}'
        elif get == 'open':
            return f'{self.OPEN_URL}/{kind}/{key}'
        elif get == 'uri':
            return f'spotify:{kind}:{key}'
        else:
            return key

    @staticmethod
    def get_request(url, headers):
        return requests.get(url, headers=headers).json()

    def search(self, query, kind, authorisation):
        """query end point, modify result types return with kind parameter"""
        url = f'{self.BASE_API}/search'  # search endpoint
        params = {'q': query, 'type': kind, 'limit': 10}
        return requests.get(url, params=params, headers=authorisation).json()[f'{kind}s']['items']

    def get_user(self, authorisation, user='self'):
        """get information on given or current user"""
        if user == 'self':
            url = f'{self.BASE_API}/me'
        else:
            url = f'{self.BASE_API}/users/{user}'

        r = requests.get(url, headers=authorisation).json()
        if user == 'self':  # update stored user
            self.user_id = r['id']

        return r

    def get_tracks(self, track_list, authorisation, limit=50, verbose=False):
        """get information for given list of tracks"""
        url = f'{self.BASE_API}/tracks'  # tracks endpoint
        results = []

        # reformat to ids only as required by API
        id_list = [self.convert(track, get='id') for track in track_list if track is not None]

        # batch ids into given limit size
        bar = range(round(len(id_list) / limit + 0.5))

        # add progress bar for very large lists of over 50 iterations
        if len(id_list) > 50:
            bar = tqdm(bar, desc=f'Getting tracks from Spotify: ',
                       unit='songs', leave=verbose, file=sys.stdout)

        # format to comma-separated list of ids and get results
        for i in bar:
            id_string = ','.join([track for track in id_list[limit * i: limit * (i + 1)]])
            results.extend(requests.get(url, params={'ids': id_string}, headers=authorisation).json()['tracks'])

        return results

    def get_all_playlists(self, authorisation, names=None, user='self', verbose=False):
        # get all information on all tracks for all given user's playlists
        if user == 'self':
            if self.user_id is None:  # get user id if not already stored
                self.get_user(authorisation)
            user = self.user_id

        # set up for loop
        playlist_results = {'next': f'{self.BASE_API}/users/{user}/playlists'}  # user playlists endpoint
        playlists = {}

        # get results, set up progress bar
        while playlist_results['next']:
            playlist_results = requests.get(playlist_results['next'],
                                            params={'limit': 50},
                                            headers=authorisation).json()
            playlist_bar = tqdm(playlist_results['items'],
                                desc='Getting Spotify playlist metadata: ',
                                unit='playlists', leave=verbose, file=sys.stdout)

            # extract track information from each playlist and add to dictionary
            for playlist in playlist_bar:
                name = playlist['name']
                if names and name not in names:  # filter to only given playlist names
                    continue

                playlist_url = playlist['href']
                playlists[name] = {'url': playlist_url,
                                   'tracks': self.get_playlist_tracks(playlist_url, authorisation)}

        return playlists

    def get_playlist_tracks(self, playlist, authorisation):
        """get all tracks from a given playlist"""
        # reformat to api link
        if 'api' not in playlist.split('.')[0] or 'tracks' not in playlist.split('/')[-1].lower():
            playlist = f"{self.convert(playlist, get='api')}/tracks"

        # set up for loop
        results = {'next': playlist}
        tracks = []

        # get results and add to list
        while results['next']:
            results = requests.get(results['next'], headers=authorisation).json()
            tracks.extend(results['items'])

        return tracks

    def create_playlist(self, playlist_name, authorisation, give='url'):
        """create an empty playlist for the current user"""
        if self.user_id is None:  # get user id if not already stored
            self.get_user(authorisation)
        url = f'{self.BASE_API}/users/{self.user_id}/playlists'  # user playlists end point

        # post message
        body = {
            "name": playlist_name,
            "description": "Generated using Syncify: https://github.com/jor-mar/syncify",
            "public": True
        }
        playlist = requests.post(url, json=body, headers=authorisation).json()['href']

        # reformat response to required format
        if give != 'url':
            return self.convert(playlist, get=give)
        else:
            return playlist

    def delete_playlist(self, playlist, authorisation):
        """unfollow a given playlist"""
        playlist = f"{self.convert(playlist, get='api')}/followers"
        r = requests.delete(playlist, headers=authorisation)
        return r.text

    @staticmethod
    def clear_playlist(playlist, authorisation, limit=100):
        playlist_url = f"{playlist['url']}/tracks"
        tracks_list = [{'uri': song['uri']} for song in playlist['tracks']]
        body = []

        for i in range(len(tracks_list) // limit + 1):
            body.append(tracks_list[limit * i: limit * (i + 1)])

        r = None
        for tracks in body:
            r = requests.delete(playlist_url, json={'tracks': tracks}, headers=authorisation)

        return r.text

    def add_to_playlist(self, playlist, track_list, authorisation, limit=50, skip_dupes=True):
        """add list of tracks to a given playlist"""
        if len(track_list) == 0:
            return

        if 'api' not in playlist.split('.')[0] or 'tracks' not in playlist.split('/')[-1]:  # reformat playlist to api
            playlist = f"{self.convert(playlist, get='api')}/tracks"

        if len(str(track_list[0]).split(':')) != 3:  # reformat tracks to URIs
            track_list = [self.convert(track, get='uri') for track in track_list if track is not None]

        current_tracks = []
        if skip_dupes:  # skip tracks currently in playlist
            current_tracks = self.get_playlist_tracks(playlist, authorisation)
            current_tracks = [track['track']['uri'] for track in current_tracks]

        # add tracks in batches
        for i in range(len(track_list) // limit + 1):
            tracks = track_list[limit * i: limit * (i + 1)]
            uri_string = ','.join([track for track in tracks if track not in current_tracks])
            requests.post(playlist, params={'uris': uri_string}, headers=authorisation)

    def uri_from_link(self, authorisation, link=None):
        if not link:
            link = input('link: ')
        link = f"{self.convert(link, get='api')}/tracks"
        r = {'next': link}
        i = 1

        while r['next']:
            r = requests.get(r['next'], headers=authorisation).json()
            print()
            for i, track in enumerate(r['items'], i):
                i = f"0{i}" if len(str(i)) == 1 else i
                if 'playlist' in link:
                    track = track['track']
                print(f"\t\"{i} - {track['name'].split(' - ')[0].strip()}\": \"{track['uri']}\",")