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
        playlists = self.get_all_playlists(authorisation, names=in_playlists)

        for values in playlists.values():
            values['tracks'] = [self.extract_track_metadata(track['track'], i)
                                for i, track in enumerate(values['tracks'])]

        if verbose:
            print('Found the following playlists:')
            max_width = len(max(playlists.keys(), key=len)) + 1

            for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
                length = str(len(playlist['tracks'])) + ' tracks'
                print(f'{name : <{max_width}}', ': ', '\33[92m', f'{length : >11} ', '\33[0m', sep='')

        return playlists

    def get_tracks_metadata(self, uri_list, authorisation, verbose=True):
        tracks = self.get_tracks(uri_list, authorisation, verbose=verbose)
        return [self.extract_track_metadata(track) for track in tracks]

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
                'year': int(re.sub('[^0-9]', '', str(track['album']['release_date']))[:4]),
                'length': track['duration_ms'] / 1000,
                'image': image_url,
                'image_height': max_height,
                'uri': track['uri']}
        return song

    def update_uris(self, m3u, spotify, verbose=True):
        max_width = len(max(spotify.keys(), key=len)) + 1
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
                    if 'uri' in song and song.get('uri') not in spotify_uris:
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
                    print('\33[92m', f'Done. Updated {i} URIs', '\33[0m', sep='')
        return {'updated': updated_uris}

    def update_playlist(self, m3u, spotify, authorisation, verbose=True):
        if len(m3u) == 0:
            return False

        max_width = len(max(spotify.keys(), key=len)) + 1

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
                            'uri' in song and song.get('uri') not in spotify_uris]
            else:
                if verbose:
                    text = f'Creating {name}...'
                    print(f"{text : <{len(text) + max_width - len(name)}}", end=' ', flush=True)

                url = self.create_playlist(name, authorisation)
                uri_list = [song['uri'] for song in songs if 'uri' in song and song.get('uri')]

            self.add_to_playlist(url, uri_list, authorisation, skip_dupes=True)

            if verbose:
                print('\33[92m', f'Done. Added {len(uri_list)} songs', '\33[0m', sep='')

        return True

    @staticmethod
    def get_differences(local, spotify, verbose=True):
        print('Getting information on differences between local and Spotify...')

        extra = {}
        missing = {}
        extra_len = 0
        missing_len = 0

        for name, songs in local.items():
            local_uris = [song['uri'] for song in songs if 'uri' in song and song['uri']]
            extra_songs = [track for track in spotify[name]['tracks'] if track['uri'] not in local_uris]
            
            spotify_uris = [track['uri'] for track in spotify[name]['tracks']]
            missing_songs = [song for song in songs if not song.get('uri') and song['uri'] not in spotify_uris]

            if len(extra_songs) != 0:
                extra[name] = extra_songs
                extra_len += len(extra_songs)

            if len(missing_songs) != 0:
                missing[name] = missing_songs
                missing_len += len(missing_songs)

        text = f'Spotify playlists have {extra_len} extra songs and \33[91m{missing_len} missing songs'
        print('\33[92m', text, '\33[0m', sep='')

        if verbose:
            max_width = len(max(missing.keys(), key=len)) + 1

            for name, playlist in sorted(missing.items(), key=lambda x: x[0].lower()):
                extra_songs = f'\33[92m+{len(extra.get(name, []))}\33[0m'
                missing_songs = f'\33[91m-{len(playlist)}\33[0m'
                print(f'{name : <{max_width}}', ':', f'{extra_songs : >14}', f'{missing_songs : >14}')

        return extra, missing

    def check_uris_on_spotify(self, playlists, authorisation, uri_file=None, verbose=True):
        if not playlists:
            if verbose:
                print('No URIs to check.')
            return
        elif isinstance(list(playlists.items())[0][1], list):
            playlists = {name: tracks for name, tracks in playlists.items() if
                         sum(['uri' in track and track.get('uri') is not None for track in tracks]) != 0}
        else:
            playlists = {name: {title: uri for title, uri in tracks.items() if uri} for name, tracks in
                         playlists.items()}

        playlist_bar = tqdm(range(len(playlists)),
                            desc='Adding to Spotify: ',
                            unit='playlists',
                            leave=verbose,
                            file=sys.stdout)
        url_list = []
        max_stops = (len(playlists) // 10) + (len(playlists) % 10 > 0)

        if uri_file:
            uri_file = join(self.DATA_PATH, uri_file + '.json')
            if sys.platform == "linux":
                os.system(f'xdg-open {uri_file}')
            elif sys.platform == "darwin":
                os.system(f'open {uri_file}')
            elif sys.platform == "win32":
                os.startfile(uri_file)

        for n, (playlist_name, songs) in enumerate(playlists.items(), 1):
            if isinstance(songs, list):
                uri_list = [song['uri'] for song in songs if 'uri' in song and song.get('uri')]
            else:
                uri_list = list(songs.values())

            if len(uri_list) == 0:
                continue

            url = f'{self.create_playlist(playlist_name, authorisation)}/tracks'
            url_list.append(url.replace('tracks', 'followers'))

            self.add_to_playlist(url, uri_list, authorisation, skip_dupes=False)

            playlist_bar.update(1)

            if len(url_list) % 10 == 0 or n == len(playlist_bar):
                text = f"\rCheck playlists and hit return to continue ({(n + 1) // 10}/{max_stops}) (enter 'q' to stop)"

                stop = input(text).strip().lower() == 'q'
                print('Deleting temporary playlists...', end='\r')
                for url in url_list:
                    if 'error' in self.delete_playlist(url, authorisation):
                        print('Refreshing token...')
                        authorisation = self.auth()
                        self.delete_playlist(url, authorisation)
                url_list = []

                if stop or n == len(playlist_bar):
                    break
                else:
                    print('Creating temporary playlists...', end='\r')
                    
        print('\33[92m', 'Check complete', ' ' * 20, '\33[0m', sep='')
        playlist_bar.close()
