import sys

import requests
from tqdm.auto import tqdm
from datetime import datetime as dt, timedelta

import json
from time import sleep

class Endpoints:

    # accepted URI types and expected id length
    _uri_types = ['track', 'playlist', 'album', 'artist', 'user', 'show', 'episode']
    _id_len = 22
    _user_id = None

    def convert(self, string: str, get: str='id', kind: str=None, **kwargs) -> str:
        """
        Converts id to required format - api/user URL, URI, or ID.

        :param string: str. URL/URI/ID to convert.
        :param get: str, default='id'. Type of string to return. Can be 'open', 'api', 'uri', 'id'.
        :param kind: str, default=None. ID type if given string is ID. 
            Examples: 'album', 'playlist', 'track', 'artist'. Refer to Spotify API for other types.
        :return: str. Formatted string
        """
        if not isinstance(string, str):  # if not string, skip checks
            return

        string = string.strip()
        
        # format for URL/URI checks
        url_check = string.split('.')[0]  # url links always start with 'open' or 'api'
        uri_check = string.split(':')  # URIs are always 3 strings separated by :

        # extract id and id types
        if 'open' in url_check or 'api' in url_check:  # open/api url
            # ensure splits give all useful information at the same indices
            url = string.replace('/v1/', '/')
            url = [i for i in url.split('/') if 'http' not in i.lower() and len(i) > 1]

            kind = url[1][:-1] if url[1][-1].lower() == 's' else url[1]
            key = url[2].split('?')[0]
        elif len(uri_check) == 3:  # URI
            kind = uri_check[1]
            key = uri_check[2]
        elif kind:  # use manually defined kind for a given id
            kind = str(kind)[:-1] if str(kind).lower().endswith('s') else str(kind).lower()
            key = string
        else:
            self._logger.error("\33[91mID given but no 'kind' defined\33[0m")
            return string

        # reformat
        if get == 'api':
            out = f'{self.BASE_API}/{kind}s/{key}'
        elif get == 'open':
            out = f'{self.OPEN_URL}/{kind}/{key}'
        elif get == 'uri':
            out = f'spotify:{kind}:{key}'
        else:
            out = key
        
        return out

    def handle_request(self, kind: str, url: str, *args, **kwargs) -> dict:
        print()
        r = getattr(requests, kind)(url, *args, **kwargs, headers=self._headers)
        while r.status_code == 429 and 'retry-after' in r.headers:
            wait_dt = dt.now() + timedelta(seconds=int(r.headers['retry-after']))
            text = f"Rate limit exceeded. Retry again at {wait_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            self._logger.warning(f"\33[91mEndpoint: {url} | {text}\33[0m")
            if int(r.headers['retry-after']) < self._test_expiry:
                self._logger.info(f"Waiting {int(r.headers['retry-after']) // 60} minutes")
                sleep(int(r.headers['retry-after']))
                r = getattr(requests, kind)(url, *args, **kwargs, headers=self._headers)
            else:
                exit(f"Wait time > {self._test_expiry // 60} minutes, exiting.")
        
        try:
            r = r.json()
        except json.decoder.JSONDecodeError:
            self._logger.error(f"Endpoint: {url} | Response: {r.text}")
        return r

    #############################################################
    ### Basic get endpoints
    #############################################################
    def query(self, query: str, kind: str, limit: int=10, **kwargs) -> list:
        """
        Query end point, modify result types return with kind parameter
        
        :param query: str. Search query.
        :param kind: str, default=None. Examples: 'album', 'track', 'artist'. Refer to Spotify API for other types.
        :param limit: int, default=10. Number of results to get.
        :return: dict. Raw results.
        """
        url = f'{self.BASE_API}/search'  # search endpoint
        params = {'q': query, 'type': kind, 'limit': limit}

        self._logger.debug(f"Endpoint: {url} | Params: {params}")

        r = self.handle_request("get", url, params=params)
        
        if 'error' in r:
            self._logger.error(f"Query failed: {query} | Response: {r['error']}")
            return []
        return r[f'{kind}s']['items']

    def get_user(self, user: str='self', **kwargs) -> dict:
        """
        Get information on given or current user
        
        :param user: str, default='self'. User ID to get, 'self' uses currently authorised user.
        :return: dict. Raw user data.
        """
        if user == 'self':  # use current user
            url = f'{self.BASE_API}/me'
        else:  # use given user
            url = f'{self.BASE_API}/users/{user}'

        self._logger.debug(f"Endpoint {url:<87}")
        r = self.handle_request("get", url)
        if user == 'self':  # update stored user
            self._user_id = r['id']
            self._logger.debug(f"User ID set to {self._user_id}")

        return r

    #############################################################
    ### Advanced tracks/items endpoints
    #############################################################
    def get_items(self, items: list, kind: str=None, limit: int=50, add_features: bool=False, add_analysis: bool=False, **kwargs) -> list:
        """
        Get information for given list of items
        
        :param items: list. List of items to get. URL/URI/ID formats accepted.
        :param kind: str, default=None. ID type if given string is ID. 
            Examples: 'album', 'track', 'artist'. Refer to Spotify API for other types.
        :param limit: int, default=50. Size of batches to request.
        :param add_features: bool, default=False. If tracks are given, search for and add features.
        :param add_analysis: bool, default=False. If tracks are given, search for and add analysis (long runtime).
        :return: list. <raw metadata for each item>
        """
        # handle user input
        kind = str(kind).lower()
        kind = kind if kind.endswith('s') else kind + "s"
        url = f'{self.BASE_API}/{kind}'  # item endpoint

        # reformat to ids only, as required by API
        id_list = [self.convert(i, get='id', kind=kind, **kwargs) for i in items if i is not None]

        # batch ids into given limit size
        item_bar = range(round(len(id_list) / limit + 0.5))

        self._logger.debug(f"Endpoint: {url} |{len(id_list):>4} {kind} |{len(item_bar):>4} pages")

        # add progress bar for large lists of over 50 iterations
        if len(id_list) > 50:
            item_bar = tqdm(item_bar, desc=f'Getting {kind}', unit=f'{kind}', leave=self._verbose, file=sys.stdout)

        results = []
        for i in item_bar:
            # format to comma-separated list of ids and get results
            id_string = ','.join([i for i in id_list[limit * i: limit * (i + 1)]])
            raw_data = self.handle_request("get", url, params={'ids': id_string})
            if kind == "tracks":
                raw_data = self.get_track_features(raw_data, **kwargs) if add_features else raw_data
                raw_data = self.get_track_analysis(raw_data, **kwargs) if add_analysis else raw_data
            results.extend(raw_data)
        
        return results

    def get_track_features(self, data, **kwargs):
        """
        Get or enrich extracted track data with audio features.
        
        :param data: str/list/dict. Track/s to get features for. URL/URI/ID formats accepted.
        :return: list/dict. Raw audio feature metadata for each item. Same type as input.
        """
        url = f'{self.BASE_API}/audio-features'  # audio features endpoint

        if isinstance(data, str):  # get features and return raw result to user
            data = self.convert(data, get="id", **kwargs)
            self._logger.debug(f"Endpoint: {url:<87} | ID: {data}")
            return self.handle_request("get", f"{url}/{data}")
        elif isinstance(data, dict) and 'id' in data:  # get features and update input
            self._logger.debug(f"Endpoint: {url} | ID: {data['id']}")
            features = self.handle_request("get", f"{url}/{data['id']}")
            data['audio_features'] = features
            return data
        elif isinstance(data, list):
            if len(data) == 0:
                self._logger.debug(f"Endpoint: {url:<87} | No data given")
                return data

            # get correctly formatted id string for endpoint
            id_string = ''
            if isinstance(data[0], str):
                id_string = ','.join(self.convert(d, get="id", **kwargs) for d in data)
            elif isinstance(data[0], dict) and 'id' in data[0]:
                id_string = ','.join(track['id'] for track in data)

            self._logger.debug(f"Endpoint: {url:<87} |{len(id_string.split(',')):>4} IDs")
            
            # get features and update input metadata
            features = self.handle_request("get", url, params={'ids': id_string})['audio_features']
            for m, f in zip(data, features):
                m['audio_features'] = f
        else:
            self._logger.warning(f"Endpoint: {url:<87} | Input data not recognised")

        return data

    def get_track_analysis(self, data, **kwargs):
        """
        Get or enrich extracted track data with audio analysis.
        
        :param data: str/list/dict. Track/s to get analysis for. URL/URI/ID formats accepted.
        :return: list/dict. Raw audio analysis metadata for each item. Same type as input.
        """
        url = f'{self.BASE_API}/audio-analysis'  # audio analysis endpoint
        endpoint_func = lambda x: self.handle_request("get", f"{url}/{x}")

        if isinstance(data, str):  # get analysis and return raw result to user
            data = self.convert(data, get="id", **kwargs)
            self._logger.debug(f"Endpoint: {url:<87} | ID: {data}")
            return endpoint_func(data)
        elif isinstance(data, dict) and 'id' in data:  # get analysis and update input
            self._logger.debug(f"Endpoint: {url:<87} | ID: {data['id']}")
            data.update(endpoint_func(data['id']))
            return data
        elif isinstance(data, list):
            if len(data) == 0:
                self._logger.debug(f"Endpoint: {url:<87} | No data given")
                return data
            
            # get id_list and analysis per track
            id_list = []
            if isinstance(data[0], str):
                id_list = [self.convert(d, get="id", **kwargs) for d in data]
            elif isinstance(data[0], dict) and 'id' in data[0]:
                id_list = [d['id'] for d in data]
            
            self._logger.debug(f"Endpoint: {url:<87} |{len(id_list):>4} IDs")
            analysis = [endpoint_func(id_) for id_ in id_list]            

            # update input metadata
            for m, a in zip(data, analysis):
                m["audio_analysis"] = a
        else:
            self._logger.warning(f"Endpoint: {url:<87} | Input data not recognised")

        return data

    #############################################################
    ### Playlist read endpoints
    #############################################################
    def get_user_playlists(self, names: list=None, user: str='self', limit: int=50, **kwargs) -> dict:
        """
        Get playlist data for a given user's playlists
        
        :param names: list, default=None. Return only these named playlists.
        :param user: str, default='self'. User ID to get, 'self' uses currently authorised user.
        :return: dict. <name>: <list of dicts of playlist's metadata>
        """
        if isinstance(names, str):  # handle names as str
            names = [names]
        
        if user == 'self':
            if self._user_id is None:  # get user id if not already stored
                self.get_user(**kwargs)
            user = self._user_id

        # user playlists endpoint
        r = {'next': f'{self.BASE_API}/users/{user}/playlists', "offset": 0}  
        playlists = {}
        
        # get results, set up progress bar
        while r['next']:
            self._logger.debug(f"Endpoint: {r['next']}")
            r = self.handle_request("get", r['next'], params={'limit': limit})

            # extract track information from each playlist and add to dictionary
            for playlist in r['items']:
                name = playlist['name']
                if names is not None and name not in names:  # filter to only given playlist names
                    continue
                playlists[name] = playlist
        
        self._logger.debug(f"Returning raw data for {len(playlists):>3} playlists")

        return playlists

    def get_playlist_tracks(self, playlist: str, limit: int=50, add_features: bool=False, add_analysis: bool=False, **kwargs) -> list:
        """
        Get all tracks from a given playlist.
        
        :param playlist: str. Playlist URL/URI/ID to get.
        :param add_features: bool, default=True. Search for and add features for each track
        :param add_analysis: bool, default=False. Search for and add features for each track (long runtime)
        :return: list. Raw track metadata for each item in the playlist.
        """
        # reformat to api link
        if isinstance(playlist, dict) and "tracks" in playlist:
            url = playlist["tracks"]["href"]
            total = playlist["tracks"]["total"]
        elif not isinstance(playlist, str):
            self._logger.error("Input data not recognised")
            return []
        else:
            url = f"{self.convert(playlist, get='api', kind='playlist', **kwargs)}/tracks"
            total = self.handle_request("get", url, params={"limit": 1})['total']

        # set up for loop
        r = {'next': url, "offset": 0, "total": total}
        tracks = []

        # get results and add to list
        while r['next']:
            self._logger.debug(f"Endpoint: {r['next']:<87} |{r['total']:>4} tracks")
            r = self.handle_request("get", r['next'], params={"limit": limit})
            raw_data = [r['track'] for r in r["items"]]
            raw_data = self.get_track_features(raw_data, **kwargs) if add_features else raw_data
            raw_data = self.get_track_analysis(raw_data, **kwargs) if add_analysis else raw_data
            tracks.extend(raw_data)
        
        for track in tracks:  # append playlist url to each track metadata
            track["playlist_url"] = url.replace("/tracks", "")
        
        self._logger.debug(f"Returning raw data{len(tracks):>4} tracks")

        return tracks

    #############################################################
    ### Playlist create/update/delete endpoints
    #############################################################
    def create_playlist(self, playlist_name: str, public: bool=True, collaborative: bool=False, **kwargs) -> str:
        """
        Create an empty playlist for the current user.
        
        :param playlist_name: str. Name of playlist to create.
        :param public: bool, default=True. Set playlist availability as public, private if False
        :return: str. API URL for playlist.
        """
        if self._user_id is None:  # get user id if not already stored
            self.get_user(**kwargs)
        url = f'{self.BASE_API}/users/{self._user_id}/playlists'  # user playlists end point

        # post message
        body = {
            "name": playlist_name,
            "description": "Generated using Syncify: https://github.com/jor-mar/syncify",
            "public": public,
            "collaborative": collaborative,
        }
        self._logger.debug(f"Endpoint: {url:<69} | Body: {body}")
        playlist = self.handle_request("post", url, json=body)['href']

        # reformat response to required format
        self._logger.debug(f"Created playlist at {playlist}")
        return playlist

    def add_to_playlist(self, playlist: str, tracks: list, limit: int=50, skip_dupes: bool=True, **kwargs) -> str:
        """
        Add list of tracks to a given playlist.
        
        :param playlist: str. Playlist URL/URI/ID to add to.
        :param tracks: list. List of tracks to add. URL/URI/ID formats accepted.
        :param limit: int, default=50. Size of batches to add.
        :param skip_dupes: bool, default=True. Skip duplicates.
        :return: str. API URL for playlist tracks.
        """
        url = f"{self.convert(playlist, get='api', kind='playlist', **kwargs)}/tracks"

        if len(tracks) == 0:
            self._logger.debug(f"Endpoint: {url:<69} | No data given")
            return        
        
        if len(str(tracks[0]).split(':')) != 3:  # reformat tracks to URIs
            tracks = [self.convert(track, get='uri', kind='track', **kwargs) for track in tracks if track is not None]

        current_tracks = []
        if skip_dupes:  # skip tracks currently in playlist
            kwargs_mod = kwargs.copy()
            for k in ['add_genre', 'add_analysis', 'add_features', 'add_raw']:
                kwargs_mod[k] = False
            current_tracks = self.get_playlist_tracks(url, **kwargs_mod)
            current_tracks = [track['track']['uri'] for track in current_tracks]

        tracks = [track for track in tracks if track not in current_tracks]
        self._logger.debug(f"Endpoint: {url:<69} | Adding {len(tracks):>3} tracks")

        # add tracks in batches
        for i in range(len(tracks) // limit + 1):
            uri_string = ','.join(tracks[limit * i: limit * (i + 1)])
            self.handle_request("post", url, params={'uris': uri_string})
        
        return url

    def delete_playlist(self, playlist: str, **kwargs) -> str:
        """
        Unfollow a given playlist.
        WARNING: This function will destructively modify your Spotify playlists.
        
        :param playlist. str. Playlist URL/URI/ID to unfollow.
        :return: str. API URL for playlist.
        """
        if not self.check_spotify_valid(playlist):
            url = self.get_user_playlists(playlist).get(playlist, {}).get('href')
            if not url:
                self._logger.warning(f"\33[91m{playlist} not found in user's playlists\33[0m")
                return
            url += "/followers"
        else:
            url = f"{self.convert(playlist, get='api', kind='playlist', **kwargs)}/followers"
        
        self._logger.debug(f"Endpoint: {url:<69}")
        r = self.handle_request("delete", url)
        return url

    def clear_from_playlist(self, playlist: list, tracks_list: list=None, limit: int=100, dry_run: bool=True, **kwargs) -> str:
        """
        Clear tracks from a given playlist.
        WARNING: This function can destructively modify your Spotify playlists.
        
        :param playlist: str/list. Playlist URL/URI/ID to clear OR list of metadata with key 'uri'.
        :param tracks_list: list. List of tracks to remove
        :param limit: int, default=100. Size of batches to clear at once, max=100.
        :return: str. API URL for playlist.
        """
        # playlists tracks endpoint
        if isinstance(playlist, dict) and 'href' in playlist.get('tracks', {}):
            url = playlist['tracks']['href']
        elif isinstance(playlist, list) and 'playlist_url' in playlist[0]:
            url = f"{playlist[0]['playlist_url']}/tracks"
        else:
            url = f"{playlist.get('url', self.convert(playlist, get='api', kind='playlist', **kwargs))}/tracks"

        # filter tracks and produce formatted params
        if tracks_list is not None:
            tracks_list = [self.convert(track, get='uri', kind="track", **kwargs) for track in tracks_list]
            tracks = [{'uri': uri}  for uri in tracks_list]
        else:
            playlist = [track for track in self.get_playlist_tracks(url, **kwargs)]
            tracks = [{'uri': track['uri']} for track in playlist]

        # split up tracks into batches of size 'limit'
        body = []
        for i in range(len(tracks) // limit + 1):
            body.append(tracks[limit * i: limit * (i + 1)])

        self._logger.debug(f"Endpoint: {url:<87} | Clearing {len(tracks):>3} tracks")
        
        count = 0
        if not dry_run:
            for tracks in body:  # delete tracks in batches
                self.handle_request("delete", url, json={'tracks': tracks})
                count += len(tracks)

        self._logger.debug(f"Endpoint: {url:<87} | Cleared {count:>3} tracks")

        return url
    
    #############################################################
    ### Misc endpoints
    #############################################################
    def print_track_uri(self, string: str=None, **kwargs) -> None:
        """
        Returns tracks from a given link in "<track>: <title> - <URI>" format for a given URL/URI.
        
        :param string: str, default=None. URL/URI to print information for. 'album' and 'playlist' types only.
        """
        if not string:  # get user to paste in URL/URI
            string = input('\33[1mEnter URL/URI: \33[0m')
        
        url = self.convert(string, get='api', **kwargs)
        self._logger.debug(f"Endpoint: {url:<87}")
        main_info = self.handle_request("get", url)
        r = {'next': f"{url}/tracks"}

        limit = 20
        i = 0

        while r['next']:
            r = self.handle_request("get", r['next'], params={'limit': limit})
            if r["offset"] == 0:
                print(f"\n\t\33[96mShowing tracks for {main_info['type']}: {main_info['name']}\33[0m\n")
                pass

            if 'error' in r:
                self._logger.warning(f"Error loading {r.get('next', url)} not found, skipping")
                return
            
            for i, track in enumerate(r['items'], i+1):
                n = f"0{i}" if len(str(i)) == 1 else i  # add leading 0 to track
                if main_info['type'] == 'playlist':  # if given link is playlist, reindex
                    track = track['track']
                print(f"\t{n}: {track['name']} - {track['uri']}")
            print()
            
            url = r['next']
