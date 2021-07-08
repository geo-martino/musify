from tqdm.auto import tqdm
import sys
import re
import requests


class Search:
            
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

                    for i, track in enumerate(album_result['tracks']['items']):
                        # time_match = abs(track['duration_ms'] / 1000 - song['length']) <= 20
                        if sum([word in track['name'].lower() for word in title]) >= title_min:
                            song['uri'] = album_result['tracks']['items'].pop(i)['uri']
                            break

            if sum(['uri' not in song for song in songs]) == 0:
                break

        songs = [self.get_track_match(song, authorisation) if 'uri' not in song else song for song in songs]

        return songs

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