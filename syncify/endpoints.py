import sys

import requests
from tqdm.auto import tqdm


class Endpoints:

    def __init__(self):

        # stores currently authorised user id
        self.user_id = None

    def convert(self, string, get='id', kind=None):
        """
        Converts id to required format - api/user URL, URI, or ID
        :param string: str. URL/URI/ID to convert.
        :param get: str, default='id'. Type of string to return. Can be 'open', 'api', 'uri', 'id'.
        :param kind: str, default=None. ID type if given string is ID. 
            Examples: 'album', 'playlist', 'track', 'artist'. Refer to Spotify API for other types.
        :return: str. Formatted string
        """
        if not string:  # if string is None, skip checks
            return

        # format for URL/URI checks
        url_check = string.split('.')[0]  # url links always start with 'open' or 'api'
        uri_check = string.split(':')  # URIs are always 3 strings separated by :

        # extract id and id types
        if 'open' in url_check or 'api' in url_check:  # url
            # ensure splits give all useful information at the same indices
            url = string.replace('/v1/', '/')
            url = [i for i in url.split('/') if 'http' not in i.lower() and len(i) > 1]

            kind = url[1][:-1] if url[1][-1].lower() == 's' else url[1]
            key = url[2].split('?')[0]
        elif len(uri_check) == 3:  # uri
            kind = uri_check[1]
            key = uri_check[2]
        elif kind:  # use manually defined kind for a given id
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
        """
        Simple get request for given url
        
        :param url: str. URL to send get request.
        :param headers: dict. Headers for authorisation.
        :return: dict. JSON response.
        """
        return requests.get(url, headers=headers).json()

    def search(self, query, kind, authorisation):
        """
        Query end point, modify result types return with kind parameter
        
        :param query: str. Search query.
        :param kind: str, default=None. Examples: 'album', 'track', 'artist'. Refer to Spotify API for other types.
        :param authorisation: dict. Headers for authorisation.
        :return: dict. JSON response.
        """
        url = f'{self.BASE_API}/search'  # search endpoint
        params = {'q': query, 'type': kind, 'limit': 10}
        return requests.get(url, params=params, headers=authorisation).json()[f'{kind}s']['items']

    def get_user(self, authorisation, user='self'):
        """
        Get information on given or current user
        
        :param authorisation: dict. Headers for authorisation.
        :param user: str, default='self'. User ID to get, 'self' uses currently authorised user.
        :return: dict. JSON response.
        """
        if user == 'self':  # use current user
            url = f'{self.BASE_API}/me'
        else:  # use given user
            url = f'{self.BASE_API}/users/{user}'

        r = requests.get(url, headers=authorisation).json()
        if user == 'self':  # update stored user
            self.user_id = r['id']

        return r

    def get_tracks(self, track_list, authorisation, limit=50, verbose=False):
        """
        Get information for given list of tracks
        
        :param track_list: list. List of tracks to get. URL/URI/ID formats accepted.
        :param authorisation: dict. Headers for authorisation.
        :param limit: int, default=50. Size of batches to request.
        :param verbose: bool, default=True. Persist progress bars if True.
        :return: list. List of information received for each track.
        """
        metadata_url = f'{self.BASE_API}/tracks'  # tracks endpoint
        features_url = f'{self.BASE_API}/audio-features'  # audio features endpoint
        results = []

        # reformat to ids only as required by API
        id_list = [self.convert(track, get='id') for track in track_list if track is not None]

        # batch ids into given limit size
        bar = range(round(len(id_list) / limit + 0.5))

        # add progress bar for very large lists of over 50 iterations
        if len(id_list) > 50:
            bar = tqdm(bar, desc='Getting tracks from Spotify: ',
                       unit='songs', leave=verbose, file=sys.stdout)

        # format to comma-separated list of ids and get results
        for i in bar:
            id_string = ','.join([track for track in id_list[limit * i: limit * (i + 1)]])
            metadata = requests.get(metadata_url, params={'ids': id_string}, headers=authorisation).json()['tracks']
            features = requests.get(features_url, params={'ids': id_string}, headers=authorisation).json()['audio_features']
            [m.update(f) for (m, f) in zip(metadata, features)]
            results.extend(metadata)

        return results

    def get_all_playlists(self, authorisation, names=None, user='self', verbose=False):
        """
        Get all information on all tracks for all given user's playlists
        
        :param authorisation: dict. Headers for authorisation.
        :param names: list, default=None. Return only these named playlists.
        :param user: str, default='self'. User ID to get, 'self' uses currently authorised user.
        :param verbose: bool, default=True. Print extra information on function running.
        :return: dict. <playlist name>: <dict of playlist url and response for tracks in playlist>
        """
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

    def get_playlist_tracks(self, playlist, authorisation, add_features=False):
        """
        Get all tracks from a given playlist.
        
        :param playlist: str. Playlist URL/URI/ID to get.
        :param authorisation: dict. Headers for authorisation.
        :return: list. List of API information received for each track in playlist.
        """
        # reformat to api link
        if 'api' not in playlist.split('.')[0] or 'tracks' not in playlist.split('/')[-1].lower():
            playlist = f"{self.convert(playlist, get='api')}/tracks"

        # set up for loop
        results = {'next': playlist}
        tracks = []
        features_url = f'{self.BASE_API}/audio-features'  # audio features endpoint

        # get results and add to list
        while results['next']:
            results = requests.get(results['next'], headers=authorisation).json()

            # reformat to ids only as required by API for getting audio features
            id_string = ','.join([track['track']['id'] for track in results['items']])
            features = requests.get(features_url, params={'ids': id_string}, headers=authorisation).json()['audio_features']
            [m['track'].update(f) for (m, f) in zip(results['items'], features)]
            tracks.extend(results['items'])

        return tracks

    def create_playlist(self, playlist_name, authorisation, give='url'):
        """
        Create an empty playlist for the current user.
        
        :param playlist_name. str. Name of playlist to create.
        :param authorisation: dict. Headers for authorisation.
        :param give: str, default='url'. Convert link to generated playlist to this given type.
        :return: str. Link as defined above.
        """
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
        """
        Unfollow a given playlist.
        
        :param playlist. str. Name of playlist to unfollow.
        :param authorisation: dict. Headers for authorisation.
        :return: str. HTML response.
        """
        playlist = f"{self.convert(playlist, get='api')}/followers"
        r = requests.delete(playlist, headers=authorisation)
        return r.text

    def clear_playlist(self, playlist, authorisation, limit=100):
        """
        Clear all songs from a given playlist.
        
        :param playlist: str/dict. Playlist URL/URI/ID to clear OR dict of metadata with keys 'url' and 'tracks'.
        :param authorisation: dict. Headers for authorisation.
        :param limit: int, default=100. Size of batches to clear at once, max=100.
        :return: str. HTML response.
        """
        # playlists tracks endpoint
        if 'url' in playlist and 'tracks' in playlist:
            playlist_url = f"{playlist['url']}/tracks"
            tracks = playlist['tracks']
        else:
            playlist_url = f"{playlist.get('url', self.convert(playlist, get='api'))}/tracks"
            tracks = [item['track'] for item in self.get_playlist_tracks(playlist_url, authorisation)]

        # formatting required for body
        tracks_list = [{'uri': song['uri']} for song in tracks]
        body = []

        # split up tracks into batches of size 'limit'
        for i in range(len(tracks_list) // limit + 1):
            body.append(tracks_list[limit * i: limit * (i + 1)])

        r = None
        for tracks in body:  # delete tracks in batches
            r = requests.delete(playlist_url, json={'tracks': tracks}, headers=authorisation)

        return r.text

    def add_to_playlist(self, playlist, track_list, authorisation, limit=50, skip_dupes=True):
        """
        Add list of tracks to a given playlist.
        
        :param playlist: str. Playlist URL/URI/ID to add to.
        :param track_list: list. List of tracks to add. URL/URI/ID formats accepted.
        :param authorisation: dict. Headers for authorisation.
        :param limit: int, default=50. Size of batches to add.
        :param skip_dupes: bool, default=True. Skip duplicates.
        """
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
        """returns tracks from a given link in "<track> - <title>": "<URI>" format for a given link.
        Useful for manual entry of URIs into stored .json file.
        
        :param authorisation: dict. Headers for authorisation.
        :param link: str, default=None. Link to print information for. Tested on 'album' and 'playlist' types only.
        """
        if not link:  # get user to paste in link
            link = input('link: ')
        link = f"{self.convert(link, get='api')}/tracks"  # reformat and tracks endpoint
        limit = 20
        r = {'next': link}
        i = 0
        j = 0

        while r['next']:
            r = requests.get(r['next'], params={'limit': limit}, headers=authorisation).json()  # get tracks information
            print()
            for i, track in enumerate(r['items'], i+1):
                n = f"0{i}" if len(str(i)) == 1 else i  # add leading 0 to track
                if 'playlist' in link:  # if given link is playlist, reindex
                    track = track['track']
                if (i - j * limit) != len(r['items']) or r['next']:
                    print(f"\t\"{n} - {track['name'].split(' - ')[0].strip().lower()}\": \"{track['uri']}\",")
                else:
                    print(f"\t\"{n} - {track['name'].split(' - ')[0].strip().lower()}\": \"{track['uri']}\"\n")
            
            j += 1
