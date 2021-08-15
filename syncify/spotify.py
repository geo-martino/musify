import os
import re
import sys
from os.path import join

from tqdm.auto import tqdm

from syncify.authorise import Authorise
from syncify.endpoints import Endpoints
from syncify.search import Search


class Spotify(Authorise, Endpoints, Search):

    def __init__(self):

        Authorise.__init__(self)
        Endpoints.__init__(self)
        Search.__init__(self)

    def get_playlists_metadata(self, authorisation, in_playlists=None, verbose=True):
        """
        Get metadata from all current user's playlists on Spotify.
        
        :param authorisation: dict. Headers for authorisation.
        :param in_playlists: list or dict, default=None. Names of playlists to get metadata from.
        :param verbose: bool, default=True. Persist progress bars if True.
        :return: dict. Spotify playlists in form <playlist name>: <dict containing <url> and <track's metadata>>
        """
        # get raw response from Spotify API on each playlist and its tracks
        playlists = self.get_all_playlists(authorisation, names=in_playlists)

        # extract and replace the raw response list with key metadata
        for values in playlists.values():
            values['tracks'] = [self.extract_track_metadata(track['track'], i)
                                for i, track in enumerate(values['tracks'])]

        if verbose:  # print no. of tracks for each playlist
            print('Found the following playlists:')

            # for appropriately aligned formatting
            max_width = len(max(playlists.keys(), key=len)) + 1

            # sort playlists in alphabetical order and print
            for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
                length = str(len(playlist['tracks'])) + ' tracks'
                print(f'{name : <{max_width}}', ': ', '\33[92m', f'{length : >11} ', '\33[0m', sep='')

        return playlists

    def get_tracks_metadata(self, uri_list, authorisation, verbose=True):
        """
        Get metadata from list given URIs
        
        :param uri_list: list. List of URIs to get metadata for.
        :param authorisation: dict. Headers for authorisation.
        :param verbose: bool, default=True. Persist progress bars if True.
        :return: list. Metadata for each track.
        """
        # request information on tracks from Spotify API and extract key metadata
        tracks = self.get_tracks(uri_list, authorisation, verbose=verbose)
        return [self.extract_track_metadata(track) for track in tracks]

    @staticmethod
    def extract_track_metadata(track, position=None):
        """
        Extract metadata for a given track from spotify API results.
        
        :param track: dict. Response from Spotify API.
        :param position: int, default=None. Add position of track in playlist to returned metadata.
        :return: dict. Metadata dict: position, title, artist, album, track, year, length, image_url, image_height, URI.
        """
        # in case of no available information
        image_url = None
        max_height = 0

        # determine largest image and get its url
        for image in track['album']['images']:
            if image['height'] > max_height:
                image_url = image['url']
                max_height = image['height']

        # create dict of metadata
        song = {'position': position,
                'title': track['name'],
                'artist': ' '.join(artist['name'] for artist in track['artists']),
                'album': track['album']['name'],
                'track': int(track['track_number']),
                'year': int(re.sub('[^0-9]', '', str(track['album']['release_date']))[:4]),
                'length': track['duration_ms'] / 1000,
                'image': image_url,
                'image_height': max_height,
                'uri': track['uri']}

        return song

    def update_uris(self, local, spotify, verbose=True):
        """
        Check and update locally stored URIs for given playlists against respective Spotify playlist's URIs.
        
        :param local: dict. Local playlists in form <playlist name>: <list of track's metadata> (incl. URIs)
        :param spotify: dict. Spotify playlists in form <playlist name>: <dict of <url> and <track's metadata (incl. URIs)>>
        :param verbose: bool, default=True. Print extra info on playlists if True.
        :return: dict. Metadata for updated tracks including old and new URIs.
        """
        # for appropriately aligned formatting
        max_width = len(max(spotify.keys(), key=len)) + 1
        updated_uris = {}

        for name, songs in local.items():  # iterate through local playlists
            if name in spotify:  # if playlist exists on Spotify
                i = 0  # count no. of updated URIs for this playlist
                if verbose:  # print information on updated URIs
                    text = f'Attempting to find URIs in Spotify playlist: {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                # list of URIs on Spotify and local URIs
                spotify_uris = [*[track['uri'] for track in spotify[name]['tracks']], None]
                m3u_uris = [song['uri'] for song in songs if 'uri' in song]
                for song in songs:
                    # determine if URI not in Spotify playlist
                    if 'uri' in song and song.get('uri') not in spotify_uris:
                        # clean track title for searching
                        title, _, _ = self.clean_tags(song)

                        # iterate through Spotify playlist to find the track
                        for track in spotify[name]['tracks']:
                            # clean Spotify track title and match
                            track_title, _, _ = self.clean_tags(track)
                            title_match = all([word in track_title for word in title.split(' ')])

                            if title_match and track['uri'] not in m3u_uris:  # update URI if match
                                i += 1

                                # get list of updated URIs if exists or return empty list to append to
                                updated_uris[name] = updated_uris.get(name, [])

                                # store old and new URI
                                song['old_uri'] = song['uri']
                                song['uri'] = track['uri']

                                # append to updated URIs for reporting
                                updated_uris[name].append(song)
                                break
                if verbose:  # no. of updated URIs for this playlist
                    print('\33[92m', f'Done. Updated {i} URIs', '\33[0m', sep='')

        return updated_uris

    def update_playlist(self, local, spotify, authorisation, verbose=True):
        """
        Takes dict of local m3u playlists with URIs as keys for each song, adding to or creating Spotify playlists.
        
        :param local: dict. Local playlists in form <playlist name>: <list of track's metadata> (incl. URIs)
        :param spotify: dict. Spotify playlists in form <playlist name>: <dict of <url> and <track's metadata (incl. URIs)>>
        :param authorisation: dict. Headers for authorisation.
        :param verbose: bool, default=True. Print extra info on playlists and persist progress bars if True.
        :return: bool. False if len(m3u) == 0, True if updated.
        """
        if len(local) == 0:  # return False if no playlists to update
            return False

        # for appropriately aligned formatting
        max_width = len(max(spotify.keys(), key=len)) + 1

        # progress bar
        playlist_bar = tqdm(reversed(local.items()),
                            desc='Adding to Spotify: ',
                            unit='playlists',
                            leave=verbose,
                            total=len(local),
                            file=sys.stdout)

        for name, songs in playlist_bar:
            if name in spotify:  # if playlist exists on Spotify
                if verbose:
                    text = f'Updating {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                # get playlist URL, list of URIs currently in Spotify playlist
                url = spotify[name]['url']
                spotify_uris = [*[track['uri'] for track in spotify[name]['tracks']], None]

                # get list of URIs from local playlists that are not already in Spotify playlist
                uri_list = [song['uri'] for song in songs if
                            'uri' in song and song.get('uri') not in spotify_uris]
            else:  # create new playlist
                if verbose:
                    text = f'Creating {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                # get newly created playlist URL, and list of URIs from local playlists
                url = self.create_playlist(name, authorisation)
                uri_list = [song['uri'] for song in songs if 'uri' in song and song.get('uri')]

            # add URIs to Spotify playlist
            self.add_to_playlist(url, uri_list, authorisation, skip_dupes=True)

            if verbose:
                print('\33[92m', f'Done. Added {len(uri_list)} songs', '\33[0m', sep='')

        return True

    @staticmethod
    def get_differences(local, spotify, verbose=True):
        """
        Produces a report on the differences between local m3u and spotify playlists.
        
        :param local: dict. Local playlists in form <playlist name>: <list of track's metadata> (incl. URIs)
        :param spotify: dict. Spotify playlists in form <playlist name>: <dict of <url> and <track's metadata (incl. URIs)>>
        :param verbose: bool, default=True. Print extra info on differences if True.
        :return: 2x dict. Metadata on extra and missing songs.
        """
        print('Getting information on differences between local and Spotify...')

        extra = {}
        missing = {}
        extra_len = 0
        missing_len = 0

        for name, songs in local.items():  # iterate through local playlists
            # get local URIs and determine which Spotify playlist URIs are not in local playlists
            local_uris = [song['uri'] for song in songs if 'uri' in song and song['uri']]
            extra_songs = [track for track in spotify[name]['tracks'] if track['uri'] not in local_uris]

            # get spotify URIs and determine which local playlist URIs are not on Spotify
            spotify_uris = [track['uri'] for track in spotify[name]['tracks']]
            missing_songs = [song for song in songs if not song.get('uri') and song.get('uri') not in spotify_uris]

            # update counts and list
            if len(extra_songs) != 0:
                extra[name] = extra_songs
                extra_len += len(extra_songs)

            if len(missing_songs) != 0:
                missing[name] = missing_songs
                missing_len += len(missing_songs)

        # print total stats
        text = f'Spotify playlists have {extra_len} extra songs and \33[91m{missing_len} missing songs'
        print('\33[92m', text, '\33[0m', sep='')

        if verbose:  # print individual playlist stats
            # for appropriately aligned formatting
            max_width = len(max(missing.keys(), key=len)) + 1

            # sort playlists in alphabetical order and print
            for name, playlist in sorted(missing.items(), key=lambda x: x[0].lower()):
                extra_songs = f'\33[92m+{len(extra.get(name, []))}\33[0m'
                missing_songs = f'\33[91m-{len(playlist)}\33[0m'
                print(f'{name : <{max_width}}', ':', f'{extra_songs : >14}', f'{missing_songs : >14}')

        return extra, missing

    def check_uris_on_spotify(self, playlists, authorisation, uri_file=None, pause=10, verbose=True):
        """
        Creates temporary playlists from locally stored URIs to check songs have an appropriate URI attached.
        User can then manually modify incorrectly associated URIs via the URIs stored in json format.
        
        :param playlists: dict. Local playlists in form <playlist name>: <list of track's metadata> (incl. URIs)
        :param authorisation: dict. Headers for authorisation.
        :param uri_file: str, default=None. If defined will automatically open this file from inside data path.
        :param pause: int, default=10. Number of temporary playlists to create before pausing to allow user to check.
        :param verbose: bool, default=True. Print extra info on playlists and persist progress bars if True.
        """
        # extract dict of <playlist name>: <list of URIs> for each playlist if URIs present
        if not playlists:  # if playlists empty, return
            if verbose:
                print('No URIs to check.')
            return
        elif isinstance(list(playlists.items())[0][1], list):  # if playlists are in <name>: <metadata list> format
            playlists = {name: [track['uri'] for track in tracks if 'uri' in track and track.get('uri')]
                         for name, tracks in playlists.items()}
        else:  # playlist given in <name>: {<title>: <URI>} format
            playlists = {name: [uri for uri in tracks.values() if uri] for name, tracks in playlists.items()}

        # progress bar
        playlist_bar = tqdm(range(len(playlists)),
                            desc='Adding to Spotify: ',
                            unit='playlists',
                            leave=verbose,
                            file=sys.stdout)

        # max stops found with round up function
        max_stops = (len(playlists) // pause) + (len(playlists) % pause > 0)

        # list of URLs of temporary playlists created
        url_list = []

        if uri_file:  # automatically open URI file if name given
            uri_file = join(self.DATA_PATH, uri_file + '.json')
            if sys.platform == "linux":
                os.system(f'xdg-open {uri_file}')
            elif sys.platform == "darwin":
                os.system(f'open {uri_file}')
            elif sys.platform == "win32":
                os.startfile(uri_file)

        # create playlists
        for n, (playlist_name, uri_list) in enumerate(playlists.items(), 1):
            if len(uri_list) == 0:  # skip creating if no URIs
                continue

            # create playlist and store it's URL
            url = f'{self.create_playlist(playlist_name, authorisation)}/tracks'
            url_list.append(url.replace('tracks', 'followers'))

            # add URIs
            self.add_to_playlist(url, uri_list, authorisation, skip_dupes=False)

            # manually update progress bar
            # manual update here makes clearer to user how many playlists have been created
            playlist_bar.update(1)

            if len(url_list) % pause == 0 or n == len(playlist_bar):  # once pause amount has been reached
                text = f"\rCheck playlists and hit return to continue ({(n + 1) // 10}/{max_stops}) (enter 'q' to stop) "
                inp = input(text)
                while self.OPEN_URL in inp:
                    self.uri_from_link(authorisation, inp)
                    inp = input(f"\n{text}")
                
                stop = inp.strip().lower() == 'q'

                print('Deleting temporary playlists...', end='\r')
                for url in url_list:  # delete playlists
                    if 'error' in self.delete_playlist(url, authorisation):  # re-authorise if necessary
                        print('Refreshing token...')
                        authorisation = self.auth()
                        self.delete_playlist(url, authorisation)
                url_list = []

                if stop or n == len(playlist_bar):  # if user has decided to quit program or all playlists created
                    break
                else:  # print verbose message
                    print('Creating temporary playlists...', end='\r')

        print('\33[92m', 'Check complete', ' ' * 20, '\33[0m', sep='')
        playlist_bar.close()
