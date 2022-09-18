import re
import sys
from time import sleep

import requests
from tqdm.auto import tqdm


class Search:

    _karaoke_tags = ['karaoke', 'backing', 'instrumental']

    _settings = {
        # len_diff = time difference in track length
        # min_diff + quick_match = words match threshold on album
        # min_diff + score_match = score match threshold on title, artist, and length
        0: {"func": "simple_match"},
        1: {
            "func": "quick_match",
            "len_diff": 15,
            "min_diff": 0.8,
            "album_title_len_match": 0.8,
            "artist_match": True,
            "artist_search": True,
        },
        2: {
            "func": "quick_match",
            "len_diff": 30,
            "min_diff": 0.66,
            "album_title_len_match": 0.6,
            "artist_match": False,
            "artist_search": True,
        },
        3: {
            "func": "score_match",
            "max_score": 1.5,
            "album_title_len_match": 0.6,
            "artist_match": False,
            "artist_search": False,
        },
        4: {"func": "simple_match"},
    }
    _neg_map = {-1: 3, -2: 5}

    @staticmethod
    def clean_tags(track: dict, **kwargs) -> dict:
        """
        Clean tags for better searching/matching.

        :param track: dict. Metadata for locally stored track.
        :return: dict. Copy of track metadata with cleaned tags.
        """
        track_clean = track.copy()
        title = track.get('title', '')
        artist = track.get('artist', '')
        album = track.get('album', '')

        # remove punctuation, strings in parentheses, feat. artists, some unnecessary words
        # make lower case, strip whitespace
        if 'title' in track and title is not None:
            title = re.sub(
                "[\\(\\[].*?[\\)\\]]",
                "",
                title).replace(
                'part ',
                ' ').replace(
                'the ',
                ' ')
            title = title.lower().replace('featuring', '').split(
                'feat.')[0].split('ft.')[0].split(' / ')[0]
            title = re.sub("[^A-Za-z0-9']+", ' ', title).strip()
            track_clean['title'] = title

        if 'artist' in track and artist is not None:
            artist = re.sub("[\\(\\[].*?[\\)\\]]", "", artist).replace('the ', ' ')
            artist = artist.lower().replace(' featuring', '').split(' feat.')[0].split(' ft.')[0]
            artist = artist.split('&')[0].split(' and ')[0].split(' vs')[0]
            artist = re.sub("[^A-Za-z0-9']+", ' ', artist).strip()
            track_clean['artist'] = artist

        if 'album' in track and album is not None:
            album = album.split('-')[0].lower().replace('ep', '')
            album = re.sub("[\\(\\[].*?[\\)\\]]", "", album).replace('the ', ' ')
            album = re.sub("[^A-Za-z0-9']+", ' ', album).strip()
            track_clean['album'] = album

        return track_clean

    #############################################################
    ## Main search handler + results handler
    #############################################################
    def search_all(self, playlists: dict, compilation: bool = None,
                   report_file: str = None, **kwargs) -> dict:
        """
        Searches all given local playlists or albums.

        :param playlists: dict. Dict of <name>: <list of dicts of track's metadata>.
        :param compilation: bool, default=None. Perform searches per track if True,
            or as one album False. If None, search list of tracks for compilation tags
            and determine if compilation.
        :param report_file: str, default=None. Name of file to output report to.
            If None, suppress file output.
        :param algo: int, default=4. Algorithm type to use for judging accurate matches.
            Search algorithms initially query <title> <artist>.
            If no results, queries <title> <album>. If no results, queries <title> only.
            Then judges matches based on the following criteria.
            Look at _settings attribute for specific settings
             0 = Returns the first result every time.
             1 = Use quick match. Use _settings = 1.
             2 = Match with 1. If no matches, use _settings = 2.
             3 = Match with 1,2. If no matches, use _settings = 3.
             4 = Match with 1,2,3. If no matches, return the first result.
            -1 = Match with _settings = 3 first.
            -2 = Match with 3. If no matches, return the first result.

        :return: dict. Report on matched, unmatched, and skipped tracks.
        """
        # filter search down
        filtered = {}
        for name, tracks in playlists.items():
            tracks = [track for track in tracks if track['uri'] is None]
            if len(tracks) > 0:
                filtered[name] = tracks
        
        if len(filtered) == 0:
            self._logger.debug(f"\33[93mNo tracks to search. \33[0m")
            return {}

        # prepare for report
        report = {}
        if isinstance(report_file, str):
            self.delete_json(report_file, **kwargs)

        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mSearching for track matches on Spotify \33[0m")

        # progress bar
        bar = tqdm(
            range(len(filtered)),
            desc='Searching',
            unit='albums',
            leave=self._verbose > 0,
            disable=self._verbose > 2 and self._verbose < 2,
            file=sys.stdout)

        # start search for each playlist/album
        for name, tracks in filtered.items():
            # sorted tracks that do/do not already have a URI and are searchable
            tracks_with_uri = [track for track in tracks if isinstance(track['uri'], str)]
            tracks_search = [track for track in tracks if track['uri'] is None]
            skipped = [track for track in tracks if track['uri'] is False] + tracks_with_uri

            # if no tracks to search, continue
            if len(tracks_search) == 0:
                # add back tracks with URI to results
                self._logger.debug(f'{name} | Skipping search, no tracks to search')
                matched = []
                unmatched = tracks_search
            else:
                if compilation is None:
                    compilation_search = self.check_compilation(tracks, **kwargs)
                else:
                    compilation_search = compilation

                if compilation_search:  # search by track
                    self._logger.debug(f'{name} | Searching with compilation algorithm')
                    if len(tracks_search) > 20:  # show progress for long playlists
                        tracks_search = tqdm(
                            tracks_search,
                            desc=name,
                            unit='tracks',
                            leave=False,
                            file=sys.stdout)
                    results = [self.get_track_match(track, **kwargs) for track in tracks_search]
                else:  # search by album
                    self._logger.debug(f'{name} | Searching with album algorithm')
                    results = self.get_album_match(tracks_search, **kwargs)

                # store tracks matched, unmatched, and skipped
                matched = [track for track in results if track['uri'] is not None]
                unmatched = [track for track in results if track['uri'] is None]

            # incrementally save report
            tmp_out = {
                "matched": {name: matched} if len(matched) > 0 else {},
                "unmatched": {name: unmatched} if len(unmatched) > 0 else {},
                "skipped": {name: skipped} if len(skipped) > 0 else {},
            }
            if len(matched) + len(unmatched) + len(skipped) > 0:
                if isinstance(report_file, str):
                    report = self.update_json(tmp_out, report_file, **kwargs)
                else:
                    for k in tmp_out:
                        report[k] = report.get(k, {}) | tmp_out[k]

            # manually update progress bar
            # manual update here makes clearer to user how many playlists have been searched
            sleep(0.1)
            bar.update(1)

        bar.close()

        self.report_log(filtered, report)

        return report

    def report_log(self, playlists: dict, report: dict) -> dict:
        """
        Logs stats on search results.

        :param playlists: dict. List of playlist names.
        :param report: dict. Report output from search
        """
        if len(playlists) == 0:
            self._logger.debug(f"\33[93mNo tracks searched. \33[0m")
            return 
        
        total_matched = 0
        total_unmatched = 0
        total_skipped = 0
        total = 0

        if self._verbose > 0:
            print()

        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        max_width = len(max(playlists, key=len)) + 1 if len(max(playlists, key=len)) + 1 < 50 else 50
        for name, tracks in playlists.items():
            matched = len(report["matched"].get(name, []))
            unmatched = len(report["unmatched"].get(name, []))
            skipped = len(report["skipped"].get(name, []))

            total_matched += matched
            total_unmatched += unmatched
            total_skipped += skipped
            total += len(tracks)

            colour1 = '\33[92m' if matched > 0 else '\33[94m'
            colour2 = '\33[92m' if unmatched == 0 else '\33[91m'
            colour3 = '\33[92m' if skipped == 0 else '\33[93m'

            logger(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                f'{colour1}{matched:>4} matched \33[0m|'
                f'{colour2}{unmatched:>4} unmatched \33[0m|'
                f'{colour3}{skipped:>4} skipped \33[0m|'
                f'\33[1m {len(tracks):>4} total \33[0m'
            )

        text = "TOTALS"
        print()
        logger(
            f"\33[1;96m{text if len(text) < 50 else text[:47] + '...':<{max_width}} \33[0m|"
            f'\33[92m{total_matched:>5} matched \33[0m|'
            f'\33[91m{total_unmatched:>5} unmatched \33[0m|'
            f'\33[93m{total_skipped:>5} skipped \33[0m|'
            f"\33[1m{total:>6} total \33[0m\n"
        )

    def get_track_results(self, track: dict, title: str = None, **kwargs) -> tuple:
        """
        Initial attempt to find a track.

        :param track: dict. Metadata for locally stored track.
        :param title: str, default=None. Original title, used for logging only.
        :return: str, list. (Query used, results)
        """
        # search <title> <artist>
        query = f"{track['title']} {track['artist']}"
        results = self.query(query, 'track', **kwargs)

        if len(results) == 0 and track['album'][:9] != 'downloads':
            # search <title> <album> if no results found
            query = f"{track['title']} {track['album']}"
            results = self.query(query, 'track', **kwargs)

        if len(results) == 0:
            # search <title> if no results found
            query = track['title']
            results = self.query(query, 'track', **kwargs)

        if len(results) == 0:
            log = "<<< Match failed: No results."
        else:
            log = f"Results: {len(results)}"

        self._logger.debug(
            f">>> {title if title else track['title']} | "
            f"Query: {query} | "
            f"{log}"
        )

        return query, results

    #############################################################
    ## Match groups (match algorithm handlers)
    #############################################################
    def get_track_match(self, track: dict, algorithm_track: int = 3, **kwargs) -> dict:
        """
        Query Spotify to get a match for given track.

        :param track: dict. Metadata for locally stored track.
        :param algorithm_track: int, default=3. The algorithm settings to use as defined above.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        # clean track metadata for searching/matching
        track_clean = self.clean_tags(track, **kwargs)
        # search
        query, results = self.get_track_results(track_clean, track['title'], **kwargs)
        # has title search already happened
        title_search = True if query == track_clean['title'] else False

        if len(results) == 0:
            # return if still no results found
            return track

        match = False
        match_algo = 0

        # search until match found or max algorithm depth reached
        while not match and abs(match_algo) <= abs(algorithm_track):
            if match_algo == 0 and algorithm_track != 0:
                # skip over performing simple match if algorithm is not 0
                match_algo = match_algo - 1 if algorithm_track < 0 else match_algo + 1
                continue

            self._logger.debug(
                f">>> {track['title']} | "
                f"Running match for algorithm: {match_algo}"
            )

            # get _settings
            if algorithm_track < 0:
                _settings = self._settings[self._neg_map[match_algo]]
            else:
                _settings = self._settings[match_algo]
            match_func = getattr(self, _settings['func'])

            # attempt matching
            if match_algo == 2:  # special conditions for algorithm 2 match
                results_title = results if title_search else self.query(
                    track_clean['title'], 'track', **kwargs)
                match = match_func(track, results_title, **_settings)
            else:
                match = match_func(track, results, **_settings)

            # increase algorithm depth
            match_algo = match_algo - 1 if algorithm_track < 0 else match_algo + 1

        return track

    def get_album_match(self, tracks: list, algorithm_album: int = 2, **kwargs) -> list:
        """
        Query Spotify to get a match for given album.

        :param tracks: list. List of dicts of metadata for locally stored tracks.
        :param algorithm_album: int, default=2. The algorithm settings to use as defined above.
        :return: list. List of dicts of metadata for locally stored album with added matched URIs if found.
        """
        album_title_len_match = self._settings[algorithm_album]["album_title_len_match"]
        match_artist = self._settings[algorithm_album]["artist_match"]
        search_artist = self._settings[algorithm_album]["artist_search"]

        # get shortest artist name from local metadata
        artist_clean = min(set(track['artist'] for track in tracks), key=len)
        # clean artist and album from local metadata
        album_clean = self.clean_tags(
            {'artist': artist_clean, 'album': tracks[0]['album']}, **kwargs)
        artist_clean = album_clean['artist']
        album_clean = album_clean['album']

        # search for album and sort by closest track number match
        query = f'{album_clean} {artist_clean}' if search_artist else album_clean
        results = self.query(query, 'album', **kwargs)
        results = sorted(results, key=lambda x: abs(x['total_tracks'] - len(tracks)))

        self._logger.debug(
            f"{tracks[0]['album']} | "
            f"Query: {query} | "
            f"Results: {len(results)} | "
            f"album_title_len_match: {album_title_len_match}"
        )

        for result in results:
            self._logger.debug(f"{tracks[0]['album']} | >>> Testing URI: {result['uri']}")
            if self.karaoke_match(tracks[0], result):
                continue

            # get tracks for result
            album_result = requests.get(result['href'], headers=self._headers).json()

            # match album
            album_match = all(word in album_result['name'].lower()
                              for word in album_clean.split(' '))
            self._logger.debug(
                f"{tracks[0]['album']} | "
                f"album_match = {album_match} | "
                f"{album_clean.split(' ')} -> {album_result['name'].lower().encode('utf-8').decode('utf-8')}"
            )

            # match artist
            artist_match = True
            if match_artist:
                # create one, spaced string from all artists on album
                artists = ' '.join([artist['name'] for artist in album_result['artists']])
                artist_match = all(word in artists.lower() for word in artist_clean.split(' '))
                self._logger.debug(
                    f"{tracks[0]['album']} | "
                    f"artist_match = {artist_match} | "
                    f"{artist_clean.split(' ')} -> {artists.lower().encode('utf-8').decode('utf-8')}"
                )

            uri_count_start = sum([isinstance(track['uri'], str) for track in tracks])
            if album_match and artist_match:
                for track in tracks:
                    if isinstance(track['uri'], str) or track['uri'] is False:
                        # skip if match already found
                        continue

                    # clean title for track local metadata and define minimum threshold words
                    # for title length match
                    title = self.clean_tags({'title': track['title']}, **kwargs)['title'].split(' ')
                    title_min = len(title) * album_title_len_match

                    for i, track_r in enumerate(album_result['tracks']['items']):
                        # time_match = abs(track_r['duration_ms'] / 1000 - track['length']) <= 20
                        # if match above threshold, match
                        track_match = sum([word in track_r['name'].lower()
                                          for word in title]) >= title_min
                        self._logger.debug(
                            f">>> {track['title']} | "
                            f"title_min = {track_match} | "
                            f"{title} -> {track_r['name'].lower().encode('utf-8').decode('utf-8')} | "
                            f"title_min = {title_min}"
                        )

                        if track_match:
                            track['uri'] = album_result['tracks']['items'].pop(i)['uri']
                            break

            uri_count_end = sum([isinstance(track['uri'], str) for track in tracks])
            self._logger.debug(
                f"{tracks[0]['album']} | "
                f"<<< Album URI  : {result['uri']} | "
                f"{uri_count_end - uri_count_start}/{len(tracks)} tracks matched"
            )

            if sum([track['uri'] is None for track in tracks]) == 0:
                # if all tracks in album are matched, break
                break

        # perform track-by-track match for any remaining tracks
        tracks = [self.get_track_match(track, **kwargs) if track['uri']
                  is None else track for track in tracks]
        matched = len([track for track in tracks if isinstance(track['uri'], str)])
        self._logger.debug(
            f"{tracks[0]['album']} | "
            f"{matched}/{len(tracks)} tracks matched"
        )

        return tracks

    #############################################################
    ## Match algorithms
    #############################################################
    def simple_match(self, track: dict, results: list, **kwargs) -> dict:
        """
        Simply use the first result as a match.

        :param track: dict. Metadata for locally stored track.
        :param results: list. Results from Spotify API for given track.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        self._logger.debug(
            f">>> {track['title']} | Begin simple match algorithm on {len(results):>2} results")
        track['uri'] = results[0]['uri']
        return track

    def title_match(self, track: dict, results: list, min_diff: int, **kwargs) -> dict:
        """
        Perform title match for a given track and its results. Useful for replacing songs in playlists.

        :param track: dict. Metadata for locally stored track.
        :param results: list. Results from Spotify API for given track.
        :param min_diff: int, default=0.8. Minimum difference in words for title matching.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        self._logger.debug(
            f">>> {track['title']} | Begin title match algorithm on {len(results):>2} results")

        for result in results:
            self._logger.debug(f">>> {track['title']} | >>> Testing URI: {result['uri']}")
            if self.karaoke_match(track, result):
                continue

            # match album name by words threshold
            title = self.clean_tags({'title': track['title']}, **kwargs)['title'].split(' ')
            title_match = sum([word in result['name'].lower()
                              for word in title]) >= len(title) * min_diff
            self._logger.debug(
                f">>> {track['title']} | "
                f"title_match = {title_match} | "
                f"{title} -> {result['name'].lower().encode('utf-8').decode('utf-8')} | "
                f"min_diff = {min_diff}"
            )

            if title_match:
                self._logger.debug(f">>> {track['title']} | <<< Matched URI: {result['uri']}")
                track['uri'] = result['uri']
                break

        return track

    def quick_match(self, track: dict, results: list, len_diff: int = 15, min_diff: int = 0.8, **kwargs) -> dict:
        """
        Perform quick match algorithm for a given track and its results.

        :param track: dict. Metadata for locally stored track.
        :param results: list. Results from Spotify API for given track.
        :param len_diff: int, default=15. Maximum difference in length of tracks for length matching.
        :param min_diff: int, default=15. Minimum difference in words for title and album matching
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        self._logger.debug(
            f">>> {track['title']} | Begin quick match algorithm on {len(results):>2} results")

        # clean tags
        clean_track = self.clean_tags(track, **kwargs)
        title = clean_track['title'].split(' ')
        album = clean_track['album'].split(' ')

        for result in results:
            self._logger.debug(f">>> {track['title']} | >>> Testing URI: {result['uri']}")
            if self.karaoke_match(track, result):
                continue

            # clean title from query results
            title_r = self.clean_tags({'title': result['name']}, **kwargs)['title']
            # title match if above threshold
            title_match = sum([word in title_r for word in title]) >= len(title) * min_diff
            self._logger.debug(
                f">>> {track['title']} | "
                f"title_match = {title_match} | "
                f"{title} -> {title_r.encode('utf-8').decode('utf-8')} | "
                f"min_diff = {min_diff}"
            )

            # match length difference
            time_match = abs(result['duration_ms'] / 1000 - track['length']) <= len_diff
            self._logger.debug(
                f">>> {track['title']} | "
                f"time_match = {time_match} | "
                f"{track['length']} -> {result['duration_ms'] / 1000} | "
                f"len_diff = {len_diff}"
            )

            # match album name by words threshold
            album_match = sum([word in result['album']['name'].lower()
                            for word in album]) >= len(album) * min_diff
            self._logger.debug(
                f">>> {track['title']} | "
                f"album_match = {album_match} | "
                f"{album} -> {result['album']['name'].lower().encode('utf-8').decode('utf-8')} | "
                f"min_diff = {min_diff}"
            )
            
            # year match - NO LONGER USED
            # year_match = track['year'] == int(
            #     re.sub('[^0-9]', '', result['album']['release_date'])[:4])
            # self._logger.debug(
            #     f">>> {track['title']} | "
            #     f"year_match = {year_match} | "
            #     f"{track['year']} -> {int(re.sub('[^0-9]', '', result['album']['release_date'])[:4])}"
            # )

            # if not karaoke and other conditions match, match track
            if title_match and any([time_match, album_match]):
                self._logger.debug(f">>> {track['title']} | <<< Matched URI: {result['uri']}")
                track['uri'] = result['uri']
                break

        return track

    def score_match(self, track: dict, results: list, max_score: int = 2, **kwargs) -> dict:
        """
        Perform score match algorithm for a given track and its results.

        :param track: dict. Cleaned metadata (use clean_track) for locally stored track.
        :param results: list. Results from Spotify API for given track.
        :param max_score: int, default=2. Stop matching once this score has been reached. Max score ceiling is 3.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """

        self._logger.debug(
            f">>> {track['title']} | Begin score match algorithm on {len(results):>2} results | max_score = {max_score}")

        # clean tags
        clean_track = self.clean_tags(track, **kwargs)
        title = clean_track['title'].split(' ')
        artist = clean_track['artist'].split(' ')

        scores = {
            "title": 0,
            "artist": 0,
            "length": 0
        }
        scores_highest = scores.copy()

        for result in results:
            scores_current = scores.copy()
            self._logger.debug(f">>> {track['title']} | >>> Testing URI: {result['uri']}")
            if self.karaoke_match(track, result):
                break

            # title score difference
            title_r = self.clean_tags({'title': result['name']}, **kwargs)['title']
            scores_current["title"] = sum([word in title_r for word in title]) / len(title)
            self._logger.debug(
                f">>> {track['title']} | "
                f"score_title = {scores_current['title']} | "
                f"{title} -> {title_r.encode('utf-8').decode('utf-8')}"
            )

            # search through all artists for match
            scores_current["artist"] = 0  # predefined as 0 in case of no artists
            for i, artist_r in enumerate(result['artists'], 1):
                artists = self.clean_tags({'artist': artist_r['name']}, **kwargs)['artist']
                scores_current["artist"] = (sum([word in artists for word in artist]) / len(artist)) * (1 / i)
            self._logger.debug(
                f">>> {track['title']} | "
                f"score_artist = {scores_current['artist']} | "
                f"{artist} -> {artists.encode('utf-8').decode('utf-8')}"
            )

            # difference in length
            scores_current["length"] = 1 - (abs(result['duration_ms'] / 1000 - track['length']) / track['length'])
            self._logger.debug(
                f">>> {track['title']} | "
                f"score_length = {scores_current['length']} | "
                f"{track['length']} -> {result['duration_ms'] / 1000}"
            )

            # log scores
            log_current = ', '.join(f'{k}={v}' for k, v in scores_current.items())
            log_highest = ', '.join(f'{k}={v}' for k, v in scores_highest.items())
            self._logger.debug(
                f">>> {track['title']} | "
                f"current: {log_current} - SUM: {sum(scores_current.values())} | "
                f"highest: {log_highest} - SUM: {sum(scores_highest.values())}"
            )

            # check if conditions match and closest length match
            if sum(scores_current.values()) > sum(scores_highest.values()):
                self._logger.debug(
                    f">>> {track['title']} | "
                    f"<<< Matched URI: {result['uri']} | "
                    f"scores: {sum(scores_current.values())} > {sum(scores_highest.values())}"
                )
                scores_highest = scores_current.copy()
                track['uri'] = result['uri']
                if sum(scores_highest.values()) >= max_score:  # prevent over-fitting
                    self._logger.debug(
                        f">>> {track['title']} | "
                        f"<<< Max score threshold reached: {sum(scores_current.values())} > {max_score}"
                    )
                    break

        return track

    #############################################################
    ## Match conditions
    #############################################################
    def karaoke_match(self, track: dict, result: dict, **kwargs) -> bool:
        """
        Checks if a result is a karaoke track/album.

        :param track: dict. Local metadata for the current track. Used for logging only.
        :param result: dict. Result from Spotify API.
        :return: bool. True if karaoke match, False if not
        """
        if "album" in result:  # this is a comp search
            album_name = result['album']['name']
            name = f">>> {track['title']}"
        else:  # this is an album search
            album_name = result['name']
            name = f"{track['album']}"

        # not a karaoke track if album doesn't contain karaoke tags
        karaoke_match = all(word in album_name.lower() for word in self._karaoke_tags)
        self._logger.debug(
            f"{name} | "
            f"not_karaoke = {not karaoke_match} | "
            f"{self._karaoke_tags} -> {album_name.lower().encode('utf-8').decode('utf-8')}"
        )

        if karaoke_match:
            return karaoke_match

        for artist_r in result['artists']:
            artists = self.clean_tags({'artist': artist_r['name']}, **kwargs)['artist']
            # not a karaoke track if artist doesn't contain karaoke tags
            karaoke_match = karaoke_match and all(word in artists for word in self._karaoke_tags)
            if karaoke_match:  # if track is karaoke, skip
                break
        self._logger.debug(
            f"{name} | "
            f"not_karaoke = {not karaoke_match}  | "
            f"{self._karaoke_tags} -> {artists.encode('utf-8').decode('utf-8')}"
        )

        return karaoke_match
