import json
import os
from ast import literal_eval
from datetime import datetime as dt
from glob import glob
from os.path import basename, dirname, join
from time import perf_counter

from local.io import LocalIO
from spotify.spotify import Spotify
from utils.authorise import AUTH_ARGS_USER as AUTH_ARGS
from utils.authorise import ApiAuthoriser
from utils.environment import Environment
from utils.io import IO
from utils.report import Report


class Syncify(Environment, ApiAuthoriser, IO, Report, LocalIO, Spotify):
    def __init__(self, verbose: bool = True, auth: bool = True, dry_run: bool = True):
        self._verbose = verbose
        self._dry_run = dry_run
        self._start_time = perf_counter()  # for measURIng total runtime
        self._start_time_filename = dt.strftime(dt.now(), '%Y-%m-%d_%H.%M.%S')

        # set up logging and attributes from environment
        Environment.__init__(self)
        self._log_path = None
        self._log_file = None
        self._auth = AUTH_ARGS
        self._logger = self.get_logger()
        self.get_env_vars()
        self._last_runs = sorted([basename(rd[0]) for rd in os.walk(dirname(self.DATA_PATH))][1:])

        # instantiate objects
        ApiAuthoriser.__init__(self, **self._auth)
        IO.__init__(self)
        Report.__init__(self)
        LocalIO.__init__(self)
        Spotify.__init__(self)

        if auth:  # get authorisation headers
            self._headers = self.auth()

        # metadata placeholders
        self._library_local = None
        self._library_spotify = None
        self._playlists_local = None
        self._playlists_spotify = None

    def convert_kwargs(self, functions, args, kwargs) -> dict:
        """Process kwargs based on user input at command line"""
        # convert all 'prefix_' kwargs lists to strings
        for k, v in kwargs.copy().items():
            if k.startswith('prefix_') and isinstance(v, list):
                kwargs[k] = ' '.join(v)
        if kwargs["filter_tags"]:
            kwargs["filter_tags"] = self.load_json(kwargs["filter_tags"], parent=True)
        if not kwargs["filter_tags"]:
            kwargs["filter_tags"] = {}

        # quickload specified, get required run as quickload folder
        if isinstance(kwargs["quickload"], str):
            kwargs["quickload"] = [r for r in self._last_runs if r.startswith(kwargs["quickload"])]
            
            if len(kwargs["quickload"]) == 0:
                kwargs["quickload"] = False
            else:
                kwargs["quickload"] = kwargs["quickload"][0]
        elif kwargs["quickload"]:
            kwargs["quickload"] = self._last_runs[-2]

        kwargs["compilation_check"] = not kwargs["compilation"]

        # parse function specific arguments
        func_args = list(functions[kwargs["function"]].values())[0]
        for k, v in zip(func_args, args):
            try:
                kwargs[k] = literal_eval(v)
            except (ValueError, SyntaxError):
                kwargs[k] = v

        return kwargs

    def get_data(self, name: str, **kwargs) -> None:
        """Get tracks from Spotify for a given name/URI/URL/ID"""

        if not self.check_spotify_valid(name):
            url = self.get_user_playlists(name, **kwargs).get(name, {}).get('href')
            if not url:
                self._logger.warning(f"\33[91m{name} not found in user's playlists \33[0m")
                return
        elif any(kind in name for kind in ['album', 'playlist']):
            self.print_track_uri(name, **kwargs)
        elif 'artist' in name:
            print(json.dumps(self.get_items([name], kind='artist', **kwargs), indent=2))
        elif 'track' in name:
            print(json.dumps(self.get_tracks_metadata([name], **kwargs), indent=2))
        else:
            self._logger.warning(f"{name} is not a valid track, album, artist, or playlist")

    #############################################################
    ## Backup/Restore
    #############################################################
    def backup(self, **kwargs) -> None:
        """Backup all URI lists for local files/playlists and Spotify playlists"""

        # backup local library
        self._library_local = self.get_local_metadata(**kwargs)
        self.save_json(self._library_local, "01_library__initial", **kwargs)
        path_uri = self.convert_metadata(self._library_local, key="path", value="uri", **kwargs)
        self.save_json(path_uri, "backup__local_library_URIs", **kwargs)

        # backup list of tracks per playlist
        self._playlists_local = self.get_m3u_metadata(**kwargs)
        self.save_json(self._playlists_local, "backup__local_playlists", **kwargs)

        # backup list of tracks per Spotify playlist
        add_extra = [{"path": track["path"], "folder": track["folder"], 'uri': track['uri']}
                    for tracks in self._library_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        self._playlists_spotify = self.get_playlists_metadata('local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "backup__spotify_playlists", **kwargs)

    def restore(self, quickload: str, kind: str, mod: str=None, **kwargs) -> None:
        """Restore  URI lists for local files/playlists and Spotify playlists
        
        :param kind: str. Restore 'local' or 'spotify'.
        :param mod: str, default=None. If kind='local', restore 'playlists' from local or restore playlists from 'spotify'
        """
        if not quickload:
            self._logger.warning("\n\33[91mSet a date to restore from using the -q flag\33[0m")
            return

        if kind == "local":
            if not mod:  # local URIs
                self._library_local = self.get_local_metadata(**kwargs)
                self.save_json(self._library_local, "01_library__initial", **kwargs)
                self.restore_local_uris(self._library_local, f"{quickload}/backup__local_library_URIs", **kwargs)
            elif mod.lower().startswith("playlist"):
                self.restore_local_playlists(f"{quickload}/backup__local_playlists", **kwargs)
            elif mod.lower().startswith("spotify"):
                self.restore_local_playlists(f"{quickload}/backup__spotify_playlists", **kwargs)
        else:  # spotify playlists
            self.restore_spotify_playlists(f"{quickload}/backup__spotify_playlists", **kwargs)


    
    #############################################################
    ## Utilities/Misc.
    #############################################################
    def missing_tags(self, **kwargs) -> None:
        """Produces report on local tracks with defined set of missing tags"""

        # loads filtered library if filtering given, entire library if not
        self._library_local = self.get_local_metadata(**kwargs)
        self.save_json(self._library_local, "01_library__initial", **kwargs)

        missing_tags = self.report_missing_tags(self._library_local, **kwargs)
        self.save_json(missing_tags, "14_library__missing_tags", **kwargs)

    def extract(self, kind: str, playlists: bool = False, **kwargs):
        """Extract and save images from local files or Spotify"""

        extract = []
        if kind == 'local':
            if not playlists:  # extract from entire local library
                extract = self.get_local_metadata(**kwargs)
                self.save_json(extract, "01_library__initial", **kwargs)
            else:  # extract from local playlists
                extract = self.get_m3u_metadata(**kwargs)
                self.save_json(extract, "10_playlists__local", **kwargs)
        elif kind == 'spotify':
            if not playlists:  # extract from Spotify for entire library
                extract = self._extract_all_from_spotify(**kwargs)
                local = self.convert_metadata(self._library_local, key="uri", value="track")

                for tracks in extract.values():
                    for track in tracks:
                        track["position"] = local[track["uri"]]
            else:  # extract from Spotify playlists
                extract = self.get_playlists_metadata('local', **kwargs)
                self.save_json(extract, "11_playlists__spotify_intial", **kwargs)
        
        self.extract_images(extract, True)

    def check(self, **kwargs) -> None:
        """Run check on entire library and update stored URIs tags"""

        # loads filtered library if filtering given, entire library if not
        self._library_local = self.get_local_metadata(**kwargs)
        self.save_json(self._library_local, "01_library__initial", **kwargs)
        path_uri = self.convert_metadata(self._library_local, key="path", value="uri", **kwargs)
        self.save_json(path_uri, "URIs_initial", **kwargs)

        self.check_tracks(self._library_local, report_file="04_report__updated_uris", **kwargs)
        self.save_json(self._library_local, "05_report__check_matches", **kwargs)
        self.save_json(self._library_local, "06_library__checked", **kwargs)

        kwargs['tags'] = ['uri']
        self.update_file_tags(self._library_local, **kwargs)

        # create backup of new URIs
        path_uri = self.convert_metadata(self._library_local, key="path", value="uri", **kwargs)
        self.save_json(path_uri, "URIs", **kwargs)
        self.save_json(path_uri, "URIs", parent=True, **kwargs)

    #############################################################
    ## Main runtime functions
    #############################################################
    def search(self, quickload, **kwargs) -> None:
        """Run all main steps up to search and check

        :param quickload: str, default=None. Date string. If set, load files from the
            folder with the given date.
        """
        #############################################################
        ## Step 1: LOAD LOCAL METADATA FOR LIBRARY
        #############################################################
        if quickload:  # load results from last search
            self._library_local = self.load_json(
                f"{quickload}/03_library__searched", parent=True, **kwargs)
        else:
            # loads filtered library if filtering given, entire library if not
            self._library_local = self.get_local_metadata(**kwargs)
            self.save_json(self._library_local, "01_library__initial", **kwargs)

            # create backup of current URIs
            path_uri = self.convert_metadata(self._library_local, key="path", value="uri", **kwargs)
            self.save_json(path_uri, "URIs_initial", **kwargs)

        #############################################################
        ## Step 2-6: SEARCH/CHECK LIBRARY
        #############################################################
        if len([t for f in self._library_local.values() for t in f if t is not None]) == 0:
            self._logger.info("All songs found or unavailable. Skipping search.")
            return

        if not quickload:  # search for missing URIs
            search_results = self.search_all(
                self._library_local, report_file="02_report__search", **kwargs)
            self.save_json(self._library_local, '03_library__searched', **kwargs)
        else:
            search_results = self.load_json(f"{quickload}/02_report__search", parent=True, **kwargs)

        # get list of paths of tracks to check
        matched = self.convert_metadata(search_results.get("matched", []), key="path", value="uri")
        unmatched = self.convert_metadata(search_results.get("unmatched", []), key="path", value="uri")
        search_paths = list(matched.keys()) + list(unmatched.keys())

        if len(search_paths) > 0:
            # get dict of filtered tracks to check from library metadata
            check_results = {}
            for name, tracks in self._library_local.items():
                for track in tracks:
                    if track['path'] in search_paths:
                        check_results[name] = check_results.get(name, []) + [track]

            if len(check_results) > 0:  # check URIs on Spotify and update with user input
                self.check_tracks(check_results, report_file="04_report__updated_uris", **kwargs)
                self.save_json(check_results, "05_report__check_matches", **kwargs)
            self.save_json(self._library_local, "06_library__checked", **kwargs)



    def _extract_all_from_spotify(self, quickload, **kwargs):
        """INTERNAL USE ONLY"""

        if quickload:
            self._library_local = self.load_json(f"{quickload}/06_library__checked", parent=True, **kwargs)
        elif self._library_local is None:  # preload if needed
            # loads filtered library if filtering given, entire library if not
            self._library_local = self.get_local_metadata(**kwargs)
            self.save_json(self._library_local, "01_library__initial", **kwargs)

        #############################################################
        ## Step 7: LOAD SPOTIFY METADATA FOR ALL TRACKS/PLAYLISTS
        #############################################################
        # extract URI list and get Spotify metadata for all tracks with URIs in local library
        add_extra = [{"path": track["path"], "folder": track["folder"], 'uri': track['uri']}
                    for tracks in self._library_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        uri_list = [metadata['uri'] for metadata in add_extra]
        self._library_spotify = self.get_tracks_metadata(uri_list, add_extra=add_extra, **kwargs)

        self.save_json(self._library_spotify, '07_spotify__library', **kwargs)

    def update_tags(self, quickload, **kwargs) -> None:
        """Run all main functions for updating local files"""

        if kwargs['tags'] is None:
            self._logger.debug(f"\33[93mNo tags set by the user.")
            return

        if quickload:
            self._library_local = self.load_json(f"{quickload}/06_library__checked", parent=True, **kwargs)
            self._library_spotify = self.load_json(f"{quickload}/07_spotify__library", parent=True, **kwargs)
        elif self._library_local is None or self._library_spotify is None:  # load if needed
            self._extract_all_from_spotify(False, **kwargs)

        #############################################################
        ## Step 8-9: TRANSFORM LOCAL TRACK METADATA, RELOAD LIBRARY
        #############################################################
        # replace local tags with spotify
        for name, tracks in self._library_local.items():
            for track in tracks:
                if track['uri'] in self._library_spotify:
                    spotify_metadata = self._library_spotify[track['uri']]
                    for tag in kwargs['tags']:
                        track[tag] = spotify_metadata.get(tag, track[tag])
                    track["image"] = spotify_metadata["image"]
        
        self.modify_compilation_tags(self._library_local, **kwargs)
        self.update_file_tags(self._library_local, **kwargs)
        self.save_json(self._library_local, '08_library__updated', **kwargs)

        # loads filtered library if filtering given, entire library if not
        self._library_local = self.get_local_metadata(**kwargs)
        self.save_json(self._library_local, "09_library__final", **kwargs)

        # create backup of new URIs
        path_uri = self.convert_metadata(self._library_local, key="path", value="uri", **kwargs)
        self.save_json(path_uri, "URIs", **kwargs)

    def update_spotify(self, quickload, **kwargs) -> None:
        """Run all main functions for updating Spotify playlists"""
        if quickload:
            self._library_local = self.load_json(f"{quickload}/09_library__final", parent=True, **kwargs)
        elif self._library_local is None:  # load if needed
            self._library_local = self.get_local_metadata(**kwargs)
            self.save_json(self._library_local, "09_library__final", **kwargs)

        #############################################################
        ## Step 10-12: UPDATE SPOTIFY PLAYLISTS, RELOAD
        #############################################################
        # get local metadata for m3u playlists
        self._playlists_local = self.get_m3u_metadata(**kwargs)
        self.save_json(self._playlists_local, "10_playlists__local", **kwargs)
        local_uri = self.convert_metadata(self._playlists_local, key="name", value="uri", **kwargs)
        self.save_json(local_uri, "URIs__local_playlists", **kwargs)

        add_extra = [{"path": track["path"], "folder": track["folder"], 'uri': track['uri']}
                    for tracks in self._library_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        self._playlists_spotify = self.get_playlists_metadata(
            'local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "11_playlists__spotify_intial", **kwargs)

        # update Spotify playlists
        self.update_playlists(self._playlists_local, **kwargs)

    def report(self, **kwargs) -> None:
        #############################################################
        ## Step 13: REPORT
        #############################################################
        if self._playlists_local is None:  # get local metadata for m3u playlists
            self._playlists_local = self.get_m3u_metadata(**kwargs)
            self.save_json(self._playlists_local, "10_playlists__local", **kwargs)
        
        # reload metadata and report
        add_extra = [{"path": track["path"], "folder": track["folder"], 'uri': track['uri']}
                    for tracks in self._library_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        self._playlists_spotify = self.get_playlists_metadata(
            'local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "12_playlists__spotify_final", **kwargs)
        playlist_uri = self.convert_metadata(
            self._playlists_spotify, key="name", value="uri", **kwargs)
        self.save_json(playlist_uri, "URIs__spotify_playlists", **kwargs)
        self._verbose = True
        report = self.report_differences(
            self._playlists_local,
            self._playlists_spotify,
            report_file="13_report__differences",
            **kwargs)

    def main(self, quickload: str = None, **kwargs) -> None:
        """Main driver function that executes primary Syncify functions"""
        self.clean_up_env(**kwargs)

        start = 0
        if quickload:
            files = glob(join(dirname(self.DATA_PATH), quickload, "*"))
            start = int(max([basename(f)[:2] for f in files if basename(f)[0].isdigit()])   )
        
        if start < 6:
            self.search(quickload, **kwargs)  # Steps 1-6
            quickload = False
        if start < 7:
            self._extract_all_from_spotify(quickload, **kwargs)  # Step 7
            quickload = False
        if start < 9:
            self.update_tags(quickload, **kwargs)  # Steps 8-9
            quickload = False
        if start < 12:
            self.update_spotify(quickload, **kwargs)  # Steps 10-12
            self.report(**kwargs)  # Step 13
            quickload = False
