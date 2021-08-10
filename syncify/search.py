import re
import sys

from tqdm.auto import tqdm


class Search:
    karaoke_tags = ['karaoke', 'backing']

    def search_all(self, playlists, authorisation, kind='playlists', add_back=False, verbose=True, algo=4):
        """
        Searches all given local playlists.
        
        :param playlists: dict. Dict of <name>: <list of track metadata> for local files to search for.
        :param authorisation: dict. Headers for authorisation.
        :param kind: str, default='playlists'. Perform searches per track for 'playlists', or as one album for 'album'.
        :param add_back: bool, default=False. Add back tracks which already have URIs on input. 
            False returns only search results.
        :param verbose: bool, default=True. Print extra information on function running.
        :param algo: int, default=4. Algorithm type to use for judging accurate matches. Not used for album queries.
            Search algorithms initially query <title> <artist>. 
            If no results, queries <title> <album>. If no results, queries <title> only.
            Then judges matches based on the following criteria.
             0 = Returns the first result every time.
             1 = Within 15s length and 66% of album names match.
             2 = If no matches from 1, use <title> query. Match within 30s length and 80% of album names match.
             3 = If no matches from 2, use best query. Match closest length with <title> and <artist> match within 66%.
             4 = If no matches from 3, use <title> query. Match closest length with <title> and <artist> match within 80%.
             5 = If no matches from 4, return the first result.
            -1 = Match with algo 3 first.
            -2 = If no matches, match with algo 4.
            -3 = If no matches, match with algo 1.
            -4 = If no matches, match with algo 2.
            -5 = If no matches, return the first result.
        
        :return results: dict. Results in <name>: <list of track metadata> like input.
        :return not_found: dict. Tracks not found in <name>: <list of track metadata> like input.
        :return searched: bool. If search has happened, returns True, else False.
        """
        results = {}
        not_found = {}
        searched = False

        # progress bar
        bar = tqdm(playlists.items(), desc='Searching: ', unit='groups', leave=verbose, file=sys.stdout)

        # start search for each playlist/album
        print('Searching with algorithm:', algo)
        for name, songs in bar:
            # songs that do/do not already have a URI
            has_uri = [song for song in songs if 'uri' in song] if add_back else []
            search_songs = [song for song in songs if 'uri' not in song]

            # if no songs to search, continue
            if len(search_songs) == 0:
                if add_back:  # add back songs with URI to results
                    results[name] = has_uri
                continue

            # else, search
            searched = True

            if kind == 'playlists':  # search by track
                if len(search_songs) > 50:  # show progress for long playlists
                    search_songs = tqdm(search_songs, desc=f'{name}: ', unit='songs', leave=verbose, file=sys.stdout)
                results[name] = [self.get_track_match(song, authorisation, algo) for song in search_songs]
            else:  # search by album
                results[name] = self.get_album_match(search_songs, authorisation)

            not_found[name] = [result for result in results[name] if 'uri' not in result]  # store not found songs
            if add_back:  # add back songs with URI to results
                results[name].extend(has_uri)

            for track in not_found[name]:  # add 'uri' key with null value to not_found results
                track['uri'] = None

            if verbose:  # verbose information on results
                colour = '\33[92m' if len(not_found[name]) == 0 else '\33[91m'
                print(colour, f'{name}: {len(not_found[name])} songs not found', '\33[0m', sep='')

        return results, not_found, searched

    def get_track_match(self, song, authorisation, algo=4):
        """
        Get match for given track.
        
        :param song: dict. Metadata for locally stored song.
        :param authorisation: dict. Headers for authorisation.
        :param algo: int, default=4. Algorithm to use for searching. Refer to search_all method documentation.
        :return: dict. Metadata for locally stored song with added matched URI if found.
        """
        # has title search already happened
        title_search = False
        # clean song metadata for searching/matching
        title_clean, artist_clean, album_clean = self.clean_tags(song)
        # initial search for <title> and <artist>
        results = self.search(f'{title_clean} {artist_clean}', 'track', authorisation)

        if len(results) == 0 and album_clean[:9] != 'downloads':  # search <title> <album> if no results found
            results = self.search(f'{title_clean} {album_clean}', 'track', authorisation)

        if len(results) == 0:  # search <title> only if no results found
            title_search = True
            results = self.search(title_clean, 'track', authorisation)

        if len(results) == 0:  # return if still no results found
            return song

        if algo == 0:  # return first result
            song['uri'] = results[0]['uri']
            return song

        if algo >= 1:  # within 15s length and 66% of album names match.
            match = self.quick_match(song, results, algo)

            if not match and algo >= 2:  # within 30s length and 80% of album names match.
                results_title = results if title_search else self.search(title_clean, 'track', authorisation)
                match = self.quick_match(song, results_title, algo)

                if not match and algo >= 3:  # closest length with <title> and <artist> match within 66%.
                    match = self.deep_match(song, results, title_clean, artist_clean, algo)

                    if not match and algo >= 4:  # match closest length with <title> and <artist> match within 80%.
                        match = self.deep_match(song, results_title, title_clean, artist_clean, algo)

                        if not match and algo >= 5:  # return first result
                            song['uri'] = results[0]['uri']

        if algo <= -1:  # closest length with <title> and <artist> match within 66%.
            match = self.deep_match(song, results, title_clean, artist_clean, 4)

            if not match and algo <= -2:  # match closest length with <title> and <artist> match within 80%.
                results_title = results if title_search else self.search(title_clean, 'track', authorisation)
                match = self.deep_match(song, results_title, title_clean, artist_clean, 3)

                if not match and algo <= -3:  # within 15s length and 66% of album names match.
                    match = self.quick_match(song, results, 1)

                    if not match and algo <= -4:  # within 30s length and 80% of album names match.
                        match = self.quick_match(song, results, 2)

                        if not match and algo <= -5:  # return first result
                            song['uri'] = results[0]['uri']

        return song

    def get_album_match(self, songs, authorisation, title_len_match=0.6):
        """
        Get match for given album.
        
        :param songs: list. List of dicts of metadata for locally stored songs.
        :param authorisation: dict. Headers for authorisation.
        :param title_len_match: float, default=0.6. Percentage of words in title to consider a match
        :return: list. List of dicts of metadata for locally stored album with added matched URIs if found.
        """
        # get base artist from local metadata
        artist = min(set(song['artist'] for song in songs), key=len)
        # clean artist and album from local metadata
        _, artist, album = self.clean_tags({'artist': artist, 'album': songs[0]['album']})

        # search for album and sort by closest track number match
        results = self.search(f'{album} {artist}', 'album', authorisation)
        results = sorted(results, key=lambda x: abs(x['total_tracks'] - len(songs)))

        for result in results:
            # get tracks for result
            album_result = self.get_request(result['href'], headers=authorisation)
            # create one string from all artists on album
            artists = ' '.join([artist['name'] for artist in album_result['artists']])

            # match album and artist
            album_match = all([word in album_result['name'].lower() for word in album.split(' ')])
            artist_match = all([word in artists.lower() for word in artist.split(' ')])

            if album_match and artist_match:
                for song in songs:
                    if 'uri' in song:  # skip if match already found
                        continue

                    # clean title for song local metadata and define minimum threshold words for title length match
                    title = self.clean_tags({'title': song['title']})[0].split(' ')
                    title_min = len(title) * title_len_match

                    for i, track in enumerate(album_result['tracks']['items']):
                        # time_match = abs(track['duration_ms'] / 1000 - song['length']) <= 20  ## UNUSED
                        # if match above threshold, match
                        if sum([word in track['name'].lower() for word in title]) >= title_min:
                            song['uri'] = album_result['tracks']['items'].pop(i)['uri']
                            break

            if sum(['uri' not in song for song in songs]) == 0:  # if all songs in album are matched, break
                break

        # perform track-by-track match for any remaining songs
        songs = [self.get_track_match(song, authorisation) if 'uri' not in song else song for song in songs]

        return songs

    @staticmethod
    def clean_tags(song):
        """
        Clean tags for better searching/matching.
        
        :param song: dict. Metadata for locally stored song.
        :return: title, artist, album cleaned tags
        """
        title = song.get('title', '')
        artist = song.get('artist', '')
        album = song.get('album', '')

        # remove punctuation, strings in parentheses, feat. artists, some unnecessary words
        # make lower case, strip whitespace
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

    def quick_match(self, song, tracks, algo=4):
        """
        Perform quick match for a given song and its results.
        
        :param song: dict. Metadata for locally stored song.
        :param tracks: list. Results from Spotify API for given song.
        :param algo: int, default=4. Algorithm to use for searching. Refer to search_all method documentation.
        :return: dict. Metadata for locally stored song with added matched URI if found. None if not found.
        """
        if algo > 2:  # 15s length match and 66% words threshold album name match
            len_diff = 15
            min_diff = 0.66
        else:  # 30s length match and 80% words threshold album name match
            len_diff = 30
            min_diff = 0.8

        for track in tracks:
            # match length difference
            time_match = abs(track['duration_ms'] / 1000 - song['length']) <= len_diff

            # match album name by words threshold
            album = self.clean_tags({'album': song['album']})[2].split(' ')
            album_match = sum([word in track['album']['name'].lower() for word in album]) >= len(album) * min_diff

            # year match
            year_match = song['year'] == int(re.sub('[^0-9]', '', track['album']['release_date'])[:4])

            # not a karaoke song if album doesn't contain karaoke tags
            not_karaoke = all([word not in track['album']['name'].lower() for word in self.karaoke_tags])

            for artist_ in track['artists']:
                # artist_name = self.clean_tags({'artist': artist_['name']})[1].split(' ')
                # not a karaoke song if artist doesn't contain karaoke tags
                not_karaoke = not_karaoke and all([word not in artist_ for word in self.karaoke_tags])
                if not not_karaoke:  # if song is karaoke, skip
                    break

            # if not karaoke and other conditions match, match song
            if any([time_match, album_match, year_match]) and not_karaoke:
                song['uri'] = track['uri']
                return song
        return None

    def deep_match(self, song, tracks, title, artist, algo=4):
        """
        Perform deeper match for a given song and its results.
        
        :param song: dict. Metadata for locally stored song.
        :param tracks: list. Results from Spotify API for given song.
        :param title: str. Cleaned title for given song.
        :param artist: str. Cleaned artist for given song.
        :param algo: int, default=4. Algorithm to use for searching. Refer to search_all method documentation.
        :return: dict. Metadata for locally stored song with added matched URI if found. None if not found.
        """
        if algo > 3:  # 66% words threshold title and artist match
            min_diff = 0.66
        else:  # 80% words threshold title and artist match
            min_diff = 0.8

        title = title.split(' ')
        artist = artist.split(' ')

        min_length_diff = 600
        for track in tracks:
            # clean title from query results
            track_name = self.clean_tags({'title': track['name']})[0]

            # title match if above threshold
            title_match = sum([word in track_name for word in title]) >= len(title) * min_diff
            artist_match = True  # predefined as True in case of no artists

            length_diff = abs(track['duration_ms'] / 1000 - song['length'])  # difference in length

            # not a karaoke song if album doesn't contain karaoke tags
            not_karaoke = all([word not in track['album']['name'].lower() for word in self.karaoke_tags])

            for artist_ in track['artists']:
                # clean artist tags for given result and check if match is above threshold
                artist_name = self.clean_tags({'artist': artist_['name']})[1]
                artist_match = sum([word in artist_name for word in artist]) >= len(artist) * min_diff

                # not a karaoke song if artist doesn't contain karaoke tags
                not_karaoke = not_karaoke and all([word not in artist_ for word in self.karaoke_tags])

                # if artists match and not karaoke, continue to check other matches
                if artist_match or not not_karaoke:
                    break

            # check if conditions match and closest length match
            if all([(artist_match or title_match), length_diff < min_length_diff, not_karaoke]):
                min_length_diff = length_diff
                song['uri'] = track['uri']
        return song
