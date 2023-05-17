import os
import re
import sys
from os.path import splitext

from tqdm.auto import tqdm

from syncify.spotify._archive.check import CheckMatches
from syncify.spotify._archive.endpoints import Endpoints
from syncify.spotify._archive.search import Search


class Spotify(Endpoints, Search, CheckMatches):

    _song_keys = {
        0: 'C',
        1: 'C#/Db',
        2: 'D',
        3: 'D#/Eb',
        4: 'E',
        5: 'F',
        6: 'F#/Gb',
        7: 'G',
        8: 'G#/Ab',
        9: 'A',
        10: 'A#/Bb',
        11: 'B'
    }

    def __init__(self):
        
        Endpoints.__init__(self)
        Search.__init__(self)
        CheckMatches.__init__(self)

    ###########################################################################
    ## Tracks
    ###########################################################################
    def extract_spotify_track_metadata(
            self, track: dict,
            position: int = None,
            add_raw: bool = False,
            add_extra: dict = None,
            **kwargs) -> dict:
        """
        Extract metadata for a given track from spotify API results.

        :param track: dict. Response from Spotify API.
        :param position: int, default=None. Position of track in a playlist.
        :param add_raw: bool, default=True. Append raw response back to final output.
        :param add_extra: dict, default=None. dict of local metadata tags to add back to response
            in the form <tag name>: <value>.
        :return: dict. Processed metadata for each track
        """
        if not track or track['uri'] is None:
            return {}
        # in case of no available information
        key = None
        image_url = None
        image_height = 0

        genre = [genre.title() for genre in track["artists"][0].get("genres", [])]
        if len(genre) == 0:
            genre = None

        if "audio_features" in track:
            f = track["audio_features"]
            key_raw = self._song_keys.get(f['key'])
            is_minor = f['mode'] == 0

            # correctly formatted song key string
            if '/' in key_raw:
                key_sep = key_raw.split('/')
                key = f"{key_sep[0]}{'m'*is_minor}/{key_sep[1]}{'m'*is_minor}"
            else:
                key = f"{key_raw}{'m'*is_minor}"

        # determine largest image and get its url
        for image in track['album']['images']:
            if image['height'] > image_height:
                image_url = image['url']
                image_height = image['height']

        # create dict of metadata
        metadata = {
            'position': position,
            'title': track['name'],
            'artist': ' '.join(artist['name'] for artist in track['artists']),
            'album': track['album']['name'],
            'track': int(track['track_number']),
            "genre": genre,
            'year': int(re.sub('\D', '', str(track['album']['release_date']))[:4]),
            'bpm': track.get("audio_features", {}).get('tempo'),
            'key': key,
            'disc': track['disc_number'],
            'image': image_url,
            'image_height': image_height,
            'length': track['duration_ms'] / 1000,
            'uri': track['uri'],
        }

        if "audio_features" in track:  # add_features
            f = track["audio_features"]

            metadata.update(
                {
                    'time_signature': f["time_signature"],
                    'acousticness': f["acousticness"],
                    'danceability': f["danceability"],
                    'energy': f["energy"],
                    'instrumentalness': f["instrumentalness"],
                    'liveness': f["liveness"],
                    'loudness': f["loudness"],
                    'speechiness': f["speechiness"],
                    'valence': f["valence"]
                }
            )

        if "audio_analysis" in track:  # add analysis
            metadata["audio_analysis"] = track["audio_analysis"]
            del track["audio_analysis"]

        if "playlist_url" in track:  # add playlist_url
            metadata['playlist_url'] = track['playlist_url']

        if add_extra:  # add extra data provided
            if 'uri' in add_extra:
                del add_extra['uri']
            metadata.update(add_extra)

        if add_raw:  # add back raw data
            metadata["raw_data"] = track

        return metadata

    def get_tracks_metadata(self, tracks: list, add_genre: bool = False,
                            add_extra: dict = None, **kwargs) -> dict:
        """
        Get metadata from list of given URIs/URLs/IDs

        :param tracks: list. List of URIs/URLs/IDs to get metadata for.
        :param add_genre: bool, default=True. Search for artists and add genres for each track.
        :param add_extra: dict, default=None. Local metadata tags to add back to response
            in the form <track URI>: <<tag name>: <value>>.
        :return: dict. <track URI>: <list of dicts of track's processed metadata>
        """
        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mExtracting Spotify metadata for {len(tracks)} tracks \33[0m")

        # request information on tracks from Spotify API and extract key metadata
        tracks = self.get_items(tracks, "track", **kwargs)
        if add_genre:  # search for the first given artist in each track
            # only search unique artists to improve runtime
            unique_artist_ids = list(set([t["artists"][0]["id"] for t in tracks]))
            artists = self.get_items(unique_artist_ids, "artist", **kwargs)
            artists = {a["uri"]: a for a in artists}

        tracks_metadata = {}
        for track in tracks:
            if add_genre:  # replace data for first given artist in each track
                track["artists"][0] = artists.get(track["artists"][0]["uri"], track["artists"][0])
            
            extra_data = None
            if isinstance(add_extra, list):  # get extra data from
                for i, extra in enumerate(add_extra):
                    if extra.get('uri') == track['uri']:
                        extra_data = extra
                        del add_extra[i]
                        break
            
            tracks_metadata[track['uri']] = self.extract_spotify_track_metadata(
                track, add_extra=extra_data, **kwargs)

        self._logger.debug('Extracting Spotify metadata: Done')
        return tracks_metadata

    ###########################################################################
    ## Playlists
    ###########################################################################
    def get_playlist_metadata(self, playlist: str, name: str = None, add_genre: bool = False,
                              add_extra: dict = None, **kwargs) -> list:
        """
        Get metadata from given playlist URI/URL/ID.

        :param playlist: str, default=None. Playlist/s to get metadata from.
        :param name: str, default=None. Name of current playlist for printing.
        :param add_genre: bool, default=False. Search for artists and add genres for each track.
        :param add_extra: list, default=None. List of local metadata tags to add back to response (must have 'uri' key to match).
        :return: list. Raw metadata for each track in the playlist
        """
        tracks = self.get_playlist_tracks(playlist, name, **kwargs)
        if add_genre:  # search for the first given artist in each track
            # only search unique artists to improve runtime
            unique_artist_ids = list(set([t["artists"][0]["id"] for t in tracks]))
            artists = self.get_items(unique_artist_ids, "artist", **kwargs)
            artists = {a["uri"]: a for a in artists}

        metadata = []
        for i, track in enumerate(tracks, 1):
            if add_genre:  # replace data for first given artist in each track
                track["artists"][0] = artists.get(track["artists"][0]["uri"], track["artists"][0])
            
            extra_data = None
            if isinstance(add_extra, list):  # get extra data from
                for i, extra in enumerate(add_extra):
                    if extra.get('uri') == track['uri']:
                        extra_data = extra
                        del add_extra[i]
                        break
            
            metadata.append(
                self.extract_spotify_track_metadata(
                    track, i, add_extra=extra_data, **kwargs))
        return metadata

    def get_playlists_metadata(self, playlists: list = 'local',
                               in_playlists: list = None,
                               ex_playlists: list = None,
                               **kwargs) -> dict:
        """
        Get metadata from all current user's playlists on Spotify.

        :param playlists: str/list/dict, default='local'. Names of playlists to get metadata from.
            None gets all. 'local' only returns playlists with names found in local playlists path.
        :param in_playlists: list, default=None. Limit playlists to those in this list.
        :param ex_playlists: list, default=None. Don't process playlists in this list.
        :return: dict. <name>: <list of dicts of track's raw metadata>
        """
        # get raw response from Spotify API on each playlist and its tracks
        if playlists == 'local':
            playlists = [splitext(playlist)[0] for playlist in os.listdir(self._playlists_path)]

        playlists_filtered = []
        for name in playlists:
            if in_playlists is not None and name.lower() not in [p.lower() for p in in_playlists]:
                continue
            elif ex_playlists is not None and name.lower() in [p.lower() for p in ex_playlists]:
                continue
            playlists_filtered.append(name)

        self._logger.debug(
            f"Filtered out {len(playlists) - len(playlists_filtered)} playlists from {len(playlists)} given playlists \33[0m")
        playlists = self.get_user_playlists(names=playlists_filtered, **kwargs)

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mGetting Spotify playlist metadata for {len(playlists)} playlists \33[0m")

        if len(playlists) == 0:
            return {}

        playlist_bar = tqdm(playlists.items(),
                            desc='Extracting metadata',
                            unit='playlists', 
                            leave=self._verbose > 0, 
                            disable=self._verbose > 2 and self._verbose < 2, 
                            file=sys.stdout)

        # extract and replace the raw response list with key metadata
        for name, playlist in playlist_bar:
            playlists[name] = self.get_playlist_metadata(playlist, name=name, **kwargs)

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        max_width = len(max(playlists, key=len)) + 1 if len(max(playlists, key=len)) + 1 < 50 else 50

        # sort playlists in alphabetical order and print
        if self._verbose > 0:
            print()
        logger("\33[1;96mFound the following Spotify playlists: \33[0m")
        for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
            logger(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                f"\33[92m{len(playlist):>5} total tracks \33[0m")

        return playlists

    def update_playlists(self, playlists: dict, clear: str = None,
                         dry_run: bool = True, **kwargs) -> bool:
        """
        Takes dict of lists of local playlists, adding to or creating Spotify playlists.
        WARNING: This function can destructively modify your Spotify playlists.

        :param playlists: dict. Local playlists in form <name>: <list of dicts of track's metadata>
        :param clear: bool, default=False. If Spotify playlist exists, clear tracks before updating.
            'all' clears all, 'extra' clears only tracks that exist in Spotify playlists, but not locally.
        :param dry_run: bool, default=True. Run function, but do not modify Spotify at all.
        :return: bool. False if len(local) == 0, True if updated.
        """
        if len(playlists) == 0:  # return False if no playlists to update
            return False

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mCreating/updating {len(playlists)} Spotify playlists \33[0m")

        # filter tracks to those with valid URIs and not containing filter tags
        playlists = self.filter_tracks(playlists, **kwargs)

        # for appropriately aligned formatting
        max_width = len(max(playlists, key=len)) + 1 if len(max(playlists, key=len)) + 1 < 50 else 50

        # progress bar
        playlist_bar = tqdm(reversed(playlists.items()),
                            desc='Adding to Spotify',
                            unit='playlists',
                            total=len(playlists),
                            leave=self._verbose > 0,
                            disable=self._verbose > 2 and self._verbose < 2, 
                            file=sys.stdout)

        # get raw metadata for current playlists on user profile
        spotify = self.get_user_playlists(names=playlists, **kwargs)

        kwargs_mod = kwargs.copy()
        for k in ['add_genre', 'add_analysis', 'add_features', 'add_raw']:
            kwargs_mod[k] = False

        for name, tracks in playlist_bar:
            uris_all = [track['uri'] for track in tracks]

            if name in spotify:  # if playlist exists on Spotify
                self._logger.debug(f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} | Updating")
                
                # get playlist tracks metadata, and list of URIs currently on Spotify
                url = spotify[name]["tracks"]["href"]
                spotify_playlist = self.get_playlist_tracks(spotify[name], name)
                uris_current = [track['uri'] for track in spotify_playlist]

                # get list of URIs from syncify.local playlists that are not already in Spotify playlist
                uris_add = [uri for uri in uris_all if uri not in uris_current]

                # clear playlist
                cleared_count = 0
                if clear == 'all':
                    self.clear_from_playlist(
                        spotify[name],
                        tracks_list=uris_current,
                        dry_run=dry_run,
                        **kwargs)
                    cleared_count = len(uris_current)
                    uris_add = uris_all
                elif clear == 'extra':
                    uris_clear = [uri for uri in uris_current if uri is not None and uri not in uris_all]
                    self.clear_from_playlist(
                        spotify[name], tracks_list=uris_clear, dry_run=dry_run, **kwargs)
                    cleared_count = len(uris_clear)

                self._logger.debug(
                    f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                    f"{len(uris_current):>4} Spotify tracks at start |"
                    f"{cleared_count:>4} Spotify tracks cleared |"
                    f"{len(uris_add):>4} tracks to add")
            else:  # create new playlist
                uris_add = uris_all

                self._logger.debug(
                    f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} | "
                    f"Creating |"
                    f"{len(uris_add):>4} tracks to add"
                )

                # get newly created playlist URL, and list of URIs from syncify.local playlists
                if not dry_run:
                    url = self.create_playlist(name, **kwargs)

            count = 0
            if not dry_run:  # add URIs to Spotify playlist
                self.add_to_playlist(url, uris_add, skip_dupes=False, **kwargs)
                count = len(uris_add)

            self._logger.debug(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} | Added {count} tracks")

        self._logger.debug('Creating/updating Spotify playlists: Done')
        return True

    def restore_spotify_playlists(self, backup: str, in_playlists: list=None, ex_playlists: list=None, **kwargs) -> dict:
        """
        Restore Spotify playlists from backup.

        :param backup: str. Filename of backup json in form <name>: <list of dicts of track's metadata>
        :param in_playlists: list, default=None. Only restore playlists in this list.
        :param ex_playlists: list, default=None. Don't restore playlists in this list.
        """
        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mRestoring Spotify playlists from backup file: {backup} \33[0m")

        backup = self.load_json(backup, parent=True, **kwargs)
        if not backup:
            self._logger.info(f"\33[91mBackup file not found.\33[0m")
            return

        if isinstance(in_playlists, str):  # handle string
            in_playlists = [in_playlists]

        if in_playlists is not None:
            for name, tracks in backup.copy().items():
                if name.lower() not in [p.lower() for p in in_playlists]:
                    del backup[name]
        else:
            in_playlists = list(backup.keys())

        if ex_playlists is not None:
            for name in backup.copy().keys():
                if name.lower() in [p.lower() for p in ex_playlists]:
                    del backup[name]

        # set clear kwarg to all
        kwargs_mod = kwargs.copy()
        kwargs_mod['clear'] = 'all'

        self.update_playlists(backup, **kwargs_mod)

        self._logger.info(f"\33[92mRestored {len(backup)} Spotify playlists \33[0m")
