import sys
import traceback
from time import sleep

from tqdm.auto import tqdm

class CheckMatches:

    #############################################################
    ### Create playlists from tracks
    #############################################################
    def check_tracks(self, playlists: dict, pause: int=10, **kwargs) -> dict:
        """
        Creates temporary playlists from locally stored URIs to check tracks have an accurate URI attached.
        User can then manually modify incorrectly associated URIs by replacing tracks in the playlists.
        
        :param playlists: dict. Local playlists in form <name>: <list of dicts of track's metadata>
        :param pause: int, default=10. Number of temporary playlists to create before pausing to allow user to check.
        :return: dict. Report on updated, unavailable, and unprocessed tracks.
        """
        report = {}

        print()
        self._logger.info('\33[1;95m -> \33[1;97mChecking matched URIs by creating temporary Spotify playlists for the user\33[0m')

        # extract dict of <name>: <list of URIs> for each playlist if URIs present
        playlist_uri_list = self.convert_metadata(playlists, key="folder", value="uri", out="list", **kwargs)
        bar = tqdm(range(len(playlist_uri_list)),
                    desc='Creating temp playlists',
                    unit='playlists',
                    leave=self._verbose,
                    file=sys.stdout)

        # max stops found with round up function
        max_stops = (len(playlists) // pause) + (len(playlists) % pause > 0)
        playlist_urls = {}  # name: URLs

        # create playlists
        for n, (playlist_name, uri_list) in enumerate(playlist_uri_list.items(), 1):
            inp = 'start'  # reset to some value to allow while loop to start
            # handle errors while still deleting temporary playlists

            try: 
                # create playlist and store it's URL for later unfollowing
                url = f'{self.create_playlist(playlist_name, public=False, **kwargs)}/tracks'
                playlist_urls[playlist_name] = url

                # add URIs 
                self.add_to_playlist(url, [uri for uri in uri_list if uri], skip_dupes=False, **kwargs)
            except:
                self._logger.error(traceback.format_exc())
                # run through to delete current playlists and exit
                n = len(playlist_uri_list)
                inp = 'q'

            # manually update progress bar
            # manual update here makes clearer to user how many playlists have been created
            sleep(0.1)
            bar.update(1)

            if len(playlist_urls) % pause == 0 or n == len(playlist_uri_list):  # once pause amount has been reached
                progress = f"{n // pause}/{max_stops}"
                if inp != 'q':
                    try:
                        print()
                        inp = self.input_check_playlists(playlists, progress)
                    except KeyboardInterrupt:
                        inp = 'q'
                if not any(inp.lower() == i for i in ['q', 's']):  # not quit or skip
                    # handle errors while still deleting temporary playlists
                    try:  # check and update URIs from any user changes
                        print()
                        report.update(self.match_tracks_from_playlists(playlists, playlist_urls, **kwargs))
                    except:
                        self._logger.error(traceback.format_exc())
                        inp = 'q'
                if not self.test_token():  # check if token has expired
                    self._logger.info('API token has expired, reauthorising...')
                    self.auth()
                
                self._logger.info(f'\33[93mDeleting {len(playlist_urls)} temporary playlists... \33[0m')
                for url in playlist_urls.values():  # delete playlists
                    self.delete_playlist(url.replace("tracks", "followers"), **kwargs)

                if inp.lower() == 'q':  # quit syncify
                    bar.leave = False
                    exit("User terminated program or failure occured.")
                elif inp.lower() == 's' or n == len(playlist_uri_list):  # skip checks
                    bar.leave = False
                    break

                # reset url_list
                playlist_urls = {}

        bar.close()
        self._logger.debug('Checking matched URIs: Done')
        
        return report

    def input_check_playlists(self, playlists: dict,  progress: str='NA', **kwargs) -> str:
        """
        Get user input for current loop of main check function.

        :param playlists: dict. <name>: <list of track's URIs>
        :param print: str, default='NA'. Progress of current loop i.e. n/n_max
        :return: str. The user's input.
        """
        options = {
            "Return": "Once all playlist's tracks are checked, continue to checking for any switches by the user",
            "Name of playlist": "Print list of URIs and positions of tracks as originally added to temp playlist",
            "Spotify link/URI": "Print position, track title, and URI from given link (useful to check current status of playlist)",
            "s": "Delete current temporary playlists and skip remaining checks",
            "q": "Delete current temporary playlists and quit Syncify",
            "h": "Show this dialogue again",
        }

        max_width = len(max(options, key=len)) + 1
        
        help_text = ["\n\t\33[96mEnter one of the following options - \33[0m\n\t"]
        for k, v in options.items():
            k += ":"
            help_text.append(f"{k:<{len(k) + max_width - len(k)}} {v}")
        help_text = '\n\t'.join(help_text) + '\n'
        print(help_text)

        inp = 'start'
        playlists_filtered = {name: [t for t in tracks if t['uri'] is not None] for name, tracks in playlists.items()}

        # if user has inputted an open url style link, print URIs for each track
        while inp != '':  # while user has not hit return only
            inp = input(f"\33[93mEnter ({progress}): \33[0m")
            inp = inp.strip()
            self._logger.debug(f"User input: {inp}")
            
            if inp.lower() == "h":  # help text
                print(help_text)
            elif self.check_spotify_valid(inp):  # print URL result
                if not self.test_token():  # check if token has expired
                    self.auth()
                self.print_track_uri(inp, **kwargs)
            elif inp.lower() in [name.lower() for name in playlists_filtered]:
                name = [name for name in playlists_filtered if name.lower() == inp.lower()][0]
                print(f"\n\tShowing tracks originally added to {name}\n")

                for i, track in enumerate(playlists_filtered[name], 1):  # print
                    i_0 = f"0{i}" if len(str(i)) == 1 else i  # add leading 0
                    print(f"\t{i_0}: {track['title']} - {track['uri']}")
            elif inp.lower() == 'q' or inp.lower() == 's':  # quit
                break

        return inp
    
    #############################################################
    ### Match to tracks user has added or removed
    #############################################################
    def match_tracks_from_playlists(self, local: dict, urls: dict, report_file: str=None, **kwargs) -> dict:
        """
        Check and update locally stored URIs for given playlists against respective Spotify playlist's URIs.
        
        :param local: dict. Local playlists in form <name>: <list of dicts of track's metadata>
        :param urls: dict. Spotify playlists in form <name>: <playlist url>
        :param report_file: str, default=None. Name of file to output report to. If None, suppress file output.
        :return: dict. Report on updated, unavailable, and unprocessed tracks.
        """
        # prepare for report
        report = {}
        if isinstance(report_file, str):
            self.delete_json(report_file, **kwargs)
        inp = ''

        for name, tracks in local.items():  # iterate through local playlists
            self._logger.debug(f">>> {name} |{len(tracks):>4} total tracks")
            if inp == 's':  # user skip function
                break
            else:  # set to value so while loop can start
                inp = 'r'

            while name in urls and inp == 'r':  # if playlist exists on Spotify or restart
                self._logger.debug(f"{name} | >>> Starting loop")
                t_switched = []
                inp = ''  # reset for next while loop

                tracks_remaining, t_switched = self.match_to_current(tracks, name=name, url=urls[name], switched=t_switched)
                if len(tracks_remaining) > 0:  # get user input for any remaining tracks
                    try:
                        inp, t_switched = self.input_missing_uris(tracks, remainder=tracks_remaining, name=name, switched=t_switched)
                    except KeyboardInterrupt:
                        inp = 's'

                # logging
                t_unavailable = [t for t in tracks if t['uri'] is False]
                t_unchanged = [t for t in tracks if t['uri'] is None]
                
                self._logger.debug(f"{name} |{len(t_switched):>4} track URIs switched")
                self._logger.debug(f"{name} |{len(t_unavailable):>4} tracks unavailable")
                self._logger.debug(f"{name} |{len(t_unchanged):>4} tracks unchanged")

                if inp != 'r':
                    updated = len(t_switched) + len(t_unavailable)
                    self._logger.debug(f"<<< {name} | {updated} tracks updated")

                # incrementally build and export report if filename set
                tmp_out = {
                    "switched": {name: t_switched} if len(t_switched) > 0 else {},
                    "unavailable": {name: t_unavailable} if len(t_unavailable) > 0 else {},
                    "unchanged": {name: t_unchanged} if len(t_unchanged) > 0 else {},
                }
                if len(t_switched) + len(t_unavailable) + len(t_unchanged) > 0:
                    if isinstance(report_file, str):
                        report = self.update_json(tmp_out, report_file, **kwargs)
                    else:
                        for k in tmp_out:
                            report[k] = report.get(k, {}) | tmp_out[k]

        return report

    def match_to_current(self, tracks: dict, name: str, url: str, switched: list, **kwargs) -> tuple:
        """
        Attempt to match missing tracks to tracks currently in a given playlist name.

        :param tracks: dict. All possible tracks for thisplaylist
            in the form <list of dicts of track's metadata>
        :param name: str. Name of the current playist for logging.
        :param url: str. URL of the playlist in which to look for missing tracks
        :param updated: list. Current list of tracks where the user has add a new URI
            in the form <list of dicts of track's metadata>
        :param max_width: int, default=0. Max width for aligned logging.
        :return: (str, dict). (user's input, <list of tracks where the user has add a new URI>)
        """
        self._logger.info(f'\33[1;95m -> \33[1;97mAttempting to find URIs for tracks in Spotify playlist: \33[94m{name}\33[0m...')

        # get list of current tracks in playlist
        if url is not None:
            kwargs_mod = kwargs.copy()
            for k in ['add_genre', 'add_analysis', 'add_features', 'add_raw']:
                kwargs_mod[k] = False
            spotify = self.get_playlist_tracks(url, **kwargs_mod)
        else:
            spotify = []

        # list of URIs on Spotify and local URIs
        spotify_uris = [*[track['uri'] for track in spotify], None, False]
        local_uris = [track['uri'] for track in tracks if track['uri']]

        # check what tracks user has added or removed
        tracks_added = {track['uri']: track for track in spotify if track['uri'] not in local_uris}
        tracks_removed = {track['path']: track for track in tracks if track['uri'] not in spotify_uris}
        tracks_missing = {track['path']: track for track in tracks if track['uri'] is None}

        if len(tracks_added) + len(tracks_removed) + len(tracks_missing) == 0:  # skip if no changes
            self._logger.debug(f"{name} | <<< No tracks switched")
            return tracks_removed | tracks_missing, switched

        self._logger.debug(f"{name} |{len(tracks_added):>4} tracks added")
        self._logger.debug(f"{name} |{len(tracks_removed):>4} tracks removed")
        self._logger.debug(f"{name} |{len(tracks_missing):>4} tracks with no URI")
        
        tracks_remaining = tracks_removed | tracks_missing
        start_len = len(tracks_remaining)
        if len(tracks_remaining) > 0:
            # attempt to match tracks removed to tracks added by title                    
            for path, track in tracks_remaining.items():
                # reset URI and find match
                track['uri'] = None
                result = self.title_match(track, results=tracks_added.values(), algo=2)

                if result['uri'] is not None:  # match found
                    # remove result from available tracks added/removed
                    del tracks_added[result['uri']]
                    if path in tracks_removed:
                        del tracks_removed[path]
                    else:
                        del tracks_missing[path]
                    switched.append(track)
            
        tracks_remaining = tracks_removed | tracks_missing
        self._logger.debug(f"{name} |{start_len - len(tracks_remaining):>4} tracks switched")
        self._logger.debug(f"{name} |{len(tracks_remaining):>4} tracks still not found")

        return tracks_remaining, switched

    def input_missing_uris(self, tracks: dict, name: str, remainder: list, switched: str, **kwargs) -> tuple:
        """
        Get user input for current loop of update URIs function.

        :param tracks: dict. All possible tracks for thisplaylist
            in the form <list of dicts of track's metadata>
        :param name: str. Name of the current playist for logging.
        :param remained: list. Current list of remaining tracks to process 
            in the form <list of dicts of track's metadata>
        :param updated: list. Current list of tracks where the user has add a new URI
            in the form <list of dicts of track's metadata>
        :return: (str, dict). (user's input, <list of tracks where the user has add a new URI>)
        """
        options = {
            "u": "Mark track as 'Unavailable on Spotify'",
            "n": "Leave track with no URI. (Syncify will still attempt to find this track at the next run)",
            "a": "Add in addition to 'u' or 's' options to apply this setting to all tracks in this playlist",
            "r": "Recheck playlist and reprompt for all tracks",
            "s": "Skip checking process for all playlists",
            "h": "Show this dialogue again",
            "OR enter a custom URI/URL/ID for this track": "",
        }
        
        help_text = [
            "\n\t\33[1;91m{name}: \33[91mThe following tracks were removed and/or matches were not found.\33[0m".format(name=name), 
            "\33[96mEnter one of the following:\33[0m\n\t"
            ]
        help_text += [f"{k}: {v}" if len(v) > 0 else k for k, v in options.items()]
        help_text = '\n\t'.join(help_text) + '\n'
        print(help_text)

        # for appropriately aligned formatting
        max_width = len(max([t['title'] for t in remainder.values()], key=len))

        self._logger.debug(f"{name} | Getting user input for {len(tracks)} tracks")

        inp = ''
        for track in tracks:
            if track['path'] not in remainder:
                # skip if track not marked as removed
                continue
            if inp == 'r' or inp == 's':
                # user quit or restart loop
                break
            if 'a' not in inp.lower():
                # reset inp value if not applying to all
                inp = ''

            while inp == '' or 'a' in inp.lower():  # wait for valid input
                if 'a' not in inp.lower():
                    text = track['title']
                    inp = input(f"\33[93m{text:<{len(text) + max_width - len(text)}}\33[0m | ")
                inp = inp.strip()
                self._logger.debug(f"{track['title']} | User input: {inp}")

                if inp.lower() == 'h':  # print help
                    print(help_text.format(name=name))
                    inp = ''
                elif inp.lower() == 's':  # skip
                    self._logger.debug(f"{name} | Skipping all loops")
                    inp = inp.lower()
                    break
                elif inp.lower() == 'r':  # restart
                    self._logger.debug(f"{name} | Refreshing playlist metadata and restarting loop")
                    inp = inp.lower()
                    break
                elif inp.lower().replace('a', '') == 'u':
                    # mark track as unavailable
                    self._logger.debug(f"{track['title']} | Marking as unavailable")
                    track['uri'] = False
                elif inp.lower().replace('a', '') == 'n':
                    # leave track without URI and unprocessed
                    self._logger.debug(f"{track['title']} | Skipping")
                    if track['uri']:
                        self._logger.debug(f"{track['title']} | Clearing URI: {track['uri']}")
                        track['uri'] = None
                elif len(inp) > 22:
                    # update URI and add track to updated URIs list
                    uri = self.convert(inp, get="uri", kind="track", **kwargs)
                    if uri.split(":")[1] != "track":  # not a valid track URI
                        inp = ''
                        continue

                    self._logger.debug(f"{track['title']} | Updating URI: {track['uri']} -> {uri}")
                    track['uri'] = uri
                    switched.append(track)
                else:  # invalid input
                    inp = ''
                
                if 'a' in inp.lower():  # go to next track
                    break
        
        return inp, switched
