import os
import re
import sys
from os.path import splitext

from tqdm.auto import tqdm

from spotify.check import CheckMatches
from spotify.endpoints import Endpoints
from spotify.search import Search


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

    #############################################################
    ### Tracks
    #############################################################
    def extract_spotify_track_metadata(self, track: dict, position: int=None, add_raw: bool=False, add_extra: dict=None, **kwargs) -> dict:
        """
        Extract metadata for a given track from spotify API results.
        
        :param track: dict. Response from Spotify API.
        :param position: int, default=None. Position of track in a playlist.
        :param add_raw: bool, default=True. Append raw response back to final output.
        :param add_extra: dict, default=None. dict of local metadata tags to add back to response
            in the form <tag name>: <value>.
        :return: dict. Processed metadata for each track
        """
        # in case of no available information
        image_url = None
        max_height = 0
        key = None

        # determine largest image and get its url
        for image in track['album']['images']:
            if image['height'] > max_height:
                image_url = image['url']
                max_height = image['height']

        if "audio_features" in track:
            f = track["audio_features"]

            # correctly formatted song key string
            if '/' in self._song_keys.get(f['key']):
                key = self._song_keys.get(f['key']).split('/')
                key = f"{key[0]}{'m'*f['mode']}/{key[1]}{'m'*f['mode']}"
            else:
                key = f"{self._song_keys.get(f['key'])}{'m'*f['mode']}"
        
        genre = ', '.join(track["artists"][0].get("genres", [])).title()
        if len(genre) == 0:
            genre = None

        # create dict of metadata
        metadata = {
            'position': position,
            'title': track['name'],
            'artist': ' '.join(artist['name'] for artist in track['artists']),
            'album': track['album']['name'],
            'track': int(track['track_number']),
            "genre": genre,
            'year': re.sub('[^0-9]', '', str(track['album']['release_date']))[:4],
            'bpm': track.get("audio_features", {}).get('tempo'),
            'key': key,
            'disc': track['disc_number'],
            'length': track['duration_ms'] / 1000,
            'image': image_url,
            'image_height': max_height,
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
            metadata.update(add_extra)
        if add_raw:  # add back raw data
            metadata["raw_data"] = track
        
        try:  # make year value int
            metadata['year'] = int(metadata['year'])
        except ValueError:
            pass
        
        return metadata

    def get_tracks_metadata(self, tracks: list, add_genre: bool=True, add_extra: dict=None, **kwargs) -> dict:
        """
        Get metadata from list of given URIs/URLs/IDs
        
        :param tracks: list. List of URIs/URLs/IDs to get metadata for.
        :param add_genre: bool, default=True. Search for artists and add genres for each track.
        :param add_extra: dict, default=None. Local metadata tags to add back to response
            in the form <track URI>: <<tag name>: <value>>.
        :return: dict. <track URI>: <list of dicts of track's processed metadata>
        """
        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mExtracting Spotify metadata for {len(tracks)} tracks\33[0m")

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
            extra_data = add_extra.get(track['uri']) if add_extra is not None else None
            tracks_metadata[track['uri']] = self.extract_spotify_track_metadata(track, add_extra=extra_data, **kwargs)
        
        self._logger.debug('Extracting Spotify metadata: Done')
        return tracks_metadata

    #############################################################
    ### Playlists
    #############################################################
    def get_playlist_metadata(self, playlist: str, add_genre: bool=False, add_extra: dict=None, **kwargs) -> list:
        """
        Get metadata from given playlist URI/URL/ID.
        
        :param playlist: str, default=None. Playlist/s to get metadata from.
        :param add_genre: bool, default=False. Search for artists and add genres for each track.
        :param add_extra: dict, default=None. Local metadata tags to add back to response.
        :return: list. Raw metadata for each track in the playlist
        """
        tracks = self.get_playlist_tracks(playlist, **kwargs)
        if add_genre:  # search for the first given artist in each track
            # only search unique artists to improve runtime
            unique_artist_ids = list(set([t["artists"][0]["id"] for t in tracks]))
            artists = self.get_items(unique_artist_ids, "artist", **kwargs)
            artists = {a["uri"]: a for a in artists}

        metadata = []
        for i, track in enumerate(tracks):
            if add_genre:  # replace data for first given artist in each track
                track["artists"][0] = artists.get(track["artists"][0]["uri"], track["artists"][0])
            extra_data = add_extra.get(track['uri']) if add_extra is not None else None
            metadata.append(self.extract_spotify_track_metadata(track, i, add_extra=extra_data, **kwargs))
        return metadata

    def get_playlists_metadata(self, playlists: list='local', in_playlists: list=None, ex_playlists: list=None, **kwargs) -> dict:
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
            playlists = [splitext(playlist)[0] for playlist in os.listdir(self._playlists_PATH)]
        
        playlists_filtered = []
        for name in playlists:
            if in_playlists is not None and name.lower() not in in_playlists:
                continue
            elif ex_playlists is not None and name.lower() in ex_playlists:
                continue
            playlists_filtered.append(name)
        
        self._logger.debug(f"Filtered out {len(playlists) - len(playlists_filtered)} playlists from {len(playlists)} given playlists\33[0m")
        playlists = self.get_user_playlists(names=playlists_filtered, **kwargs)
        
        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mGetting Spotify playlist metadata for {len(playlists)} playlists\33[0m")

        playlist_bar = tqdm(playlists.items(),
                            desc='Extracting metadata',
                            unit='playlists', leave=self._verbose, file=sys.stdout)

        # extract and replace the raw response list with key metadata
        for name, playlist in playlist_bar:
            playlists[name] = self.get_playlist_metadata(playlist, **kwargs)

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose else self._logger.debug
        max_width = len(max(playlists, key=len))

        # sort playlists in alphabetical order and print
        if self._verbose:
            print()
        logger("\33[1;96mFound the following Spotify playlists:\33[0m")
        for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
            logger(f"{name:<{max_width}} |\33[92m{len(playlist):>4} total tracks\33[0m")

        return playlists

    def update_playlists(self, playlists: dict, clear: str=None, dry_run: bool=True, **kwargs) -> bool:
        """
        Takes dict of lists of local playlists, adding to or creating Spotify playlists.
        WARNING: This function can destructively modify your Spotify playlists.
        
        :param playlists: dict. Local playlists in form <name>: <list of dicts of track's metadata>
        :param clear: bool, default=False. If Spotify playlist exists, clear tracks before updating.
            'all' clears all, 'extra' clears only tracks that exist in Spotify playlists, but not locally.
        :param dry_run: bool, default=False. Run function, but do not modify Spotify at all.
        :return: bool. False if len(local) == 0, True if updated.
        """
        if len(playlists) == 0:  # return False if no playlists to update
            return False

        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mCreating/updating {len(playlists)} Spotify playlists\33[0m")

        # filter tracks to those with valid URIs and not containing filter tags
        playlists = self.filter_tracks(playlists, **kwargs)

        # for appropriately aligned formatting
        max_width = len(max(playlists, key=len))

        # progress bar
        playlist_bar = tqdm(reversed(playlists.items()),
                            desc='Adding to Spotify',
                            unit='playlists',
                            total=len(playlists),
                            leave=self._verbose,
                            file=sys.stdout)
        
        # get raw metadata for current playlists on user profile
        spotify = self.get_user_playlists(names=playlists, **kwargs)
        
        kwargs_mod = kwargs.copy()
        for k in ['add_genre', 'add_analysis', 'add_features', 'add_raw']:
            kwargs_mod[k] = False

        for name, tracks in playlist_bar:
            uris_all = [track['uri'] for track in tracks]
        
            if name in spotify:  # if playlist exists on Spotify
                self._logger.debug(f"{name:<{len(name) + max_width - len(name)}} | Updating")

                # get playlist tracks metadata, and list of URIs currently on Spotify
                spotify_playlist = self.get_playlist_tracks(spotify[name])
                uris_current = [track['uri'] for track in spotify_playlist]

                # get list of URIs from local playlists that are not already in Spotify playlist
                uris_add = [uri for uri in uris_all if uri not in uris_current]

                # clear playlist
                cleared_count = 0
                if clear == 'all':
                    self.clear_from_playlist(spotify[name], tracks_list=uris_current, dry_run=dry_run, **kwargs)
                    cleared_count = len(uris_current)
                    uris_add = uris_all
                elif clear == 'extra':
                    clear = [uri for uri in uris_current if uri not in uris_all]
                    self.clear_from_playlist(spotify[name], tracks_list=clear, dry_run=dry_run, **kwargs)
                    cleared_count = len(clear)

                self._logger.debug(
                    f"{name:<{len(name) + max_width - len(name)}} |"
                    f"{len(uris_current):>4} Spotify tracks at start |"
                    f"{cleared_count:>4} Spotify tracks cleared |"
                    f"{len(uris_add):>4} tracks to add")
            else:  # create new playlist
                uris_add = uris_all

                self._logger.debug(
                    f"{name:<{len(name) + max_width - len(name)}} | "
                    f"Creating |"
                    f"{len(uris_add):>4} tracks to add"
                    )

                # get newly created playlist URL, and list of URIs from local playlists
                if not dry_run:
                    url = self.create_playlist(name, **kwargs)

            count = 0
            if not dry_run:  # add URIs to Spotify playlist
                self.add_to_playlist(url, uris_add, skip_dupes=False, **kwargs)
                count = len(uris_add)

            self._logger.debug(f"{name:<{len(name) + max_width - len(name)}} | Added {count} tracks")

        self._logger.debug('Creating/updating Spotify playlists: Done')
        return True

    def restore_spotify_playlists(self, playlists: list, backup: str, **kwargs) -> dict:
        """
        Restore Spotify playlists from backup.

        :param playlists: str/list/dict. Metadata in form <name>: <list of dicts of track's metadata>
            None restores all from backup.
        :param backup: str. Filename of backup json in form <name>: <list of dicts of track's metadata>
        :return: dict. <name>: <list of dicts of track's metadata>
        """
        self._logger.info(f"Restoring Spotify from backup file: {backup}")

        backup = self.load_json(backup, **kwargs)
        if not backup:
            return

        if isinstance(playlists, str):  # handle string and None
            playlists = [playlists]
        elif playlists == None:
            playlists = list(backup.keys())
        
        # set clear kwarg to all
        kwargs_mod = kwargs.copy()
        kwargs_mod['clear'] = 'all'
        
        for name in backup:
            if name not in playlists:
                continue
            
            self.update_playlists(backup, **kwargs_mod)

        return playlists