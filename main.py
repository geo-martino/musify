import argparse
import json
import os
import traceback
from ast import literal_eval
from datetime import datetime as dt
from os.path import basename, dirname, join
from time import perf_counter
from glob import glob

from dotenv import load_dotenv

# load stored environment variables from .env
load_dotenv()

from local.io import LocalIO
from spotify.spotify import Spotify
from utils.authorise import AUTH_ARGS_USER as AUTH_ARGS
from utils.authorise import ApiAuthoriser
from utils.environment import Environment
from utils.io import IO
from utils.report import Report




class Syncify(Environment, ApiAuthoriser, IO, Report, LocalIO, Spotify):
    def __init__(self, verbose: bool = True, auth: bool = True, dry_run: bool = False):
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
        self.get_env_vars(dry_run)
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

    def get_data(self, name: str, **kwargs) -> None:
        """Get tracks from Spotify for a given name/URI/URL/ID"""

        if not self.check_spotify_valid(name):
            url = self.get_user_playlists(name).get(name, {}).get('href')
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
        self.save_json(path_uri, "URIs__local_library", **kwargs)

        # backup list of tracks per playlist
        self._playlists_local = self.get_m3u_metadata(**kwargs)
        self.save_json(self._playlists_local, "10_playlists__local", **kwargs)
        local_uri = self.convert_metadata(self._playlists_local, key="name", value="uri", **kwargs)
        self.save_json(local_uri, "URIs__local_playlists", **kwargs)

        # backup list of tracks per Spotify playlist
        self._playlists_spotify = self.get_playlists_metadata('local', **kwargs)
        self.save_json(self._playlists_spotify, "11_playlists__spotify", **kwargs)
        spotify_uri = self.convert_metadata(
            self._playlists_spotify, key="name", value="uri", **kwargs)
        self.save_json(spotify_uri, "URIs__spotify_playlists", **kwargs)

    def restore(self, kind: str, playlists: bool, **kwargs) -> None:
        # TODO: restore local URI tags from backup + restore spotify playlists from backup

        if kind == "local":
            if playlists:  # local URIs
                pass
            else:  # local playlists
                pass
        else:  # spotify playlists
            pass
    
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
        if not quickload:  # search for missing URIs
            search_results = self.search_all(
                self._library_local, report_file="02_report__search", **kwargs)
            self.save_json(self._library_local, '03_library__searched', **kwargs)
        else:
            search_results = self.load_json(f"{quickload}/02_report__search", parent=True, **kwargs)

        # get list of paths of tracks to check
        matched = self.convert_metadata(search_results["matched"], key="path", value="uri")
        unmatched = self.convert_metadata(search_results["unmatched"], key="path", value="uri")
        search_paths = list(matched.keys()) + list(unmatched.keys())

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
        uri_list = [track['uri'] for tracks in self._library_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        add_extra = {}
        for tracks in self._library_local.values():
            for track in tracks:
                if track['uri'] in uri_list:
                    add_extra[track['uri']] = {"folder": track["folder"], "path": track["path"]}
        self._library_spotify = self.get_tracks_metadata(uri_list, add_extra=add_extra, **kwargs)

        save_data = {}
        for track in self._library_spotify.values():
            # convert to folder: track structure like local data for saving
            folder = track["folder"]
            save_data[folder] = save_data.get(folder, []) + [track]
        self.save_json(save_data, '07_spotify__library', **kwargs)

        return save_data

    def update_tags(self, quickload, **kwargs) -> None:
        """Run all main functions for updating local files"""

        self._extract_all_from_spotify(quickload, **kwargs)

        #############################################################
        ## Step 8-9: TRANSFORM LOCAL TRACK METADATA, RELOAD LIBRARY
        #############################################################
        # replace local tags with spotify
        for name, tracks in self._library_local.items():
            for track in tracks:
                if track['uri'] in self._library_spotify:
                    spotify_metadata = self._library_spotify[track['uri']]
                    for tag in track:
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
        #############################################################
        ## Step 10-13: UPDATE SPOTIFY PLAYLISTS, RELOAD, REPORT
        #############################################################
        # get local metadata for m3u playlists
        self._playlists_local = self.get_m3u_metadata(**kwargs)
        self.save_json(self._playlists_local, "10_playlists__local", **kwargs)
        local_uri = self.convert_metadata(self._playlists_local, key="name", value="uri", **kwargs)
        self.save_json(local_uri, "URIs__local_playlists", **kwargs)

        uri_list = [track['uri'] for tracks in self._playlists_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        add_extra = {}
        for tracks in self._playlists_local.values():
            for track in tracks:
                if track['uri'] in uri_list:
                    add_extra[track['uri']] = {"folder": track["folder"], "path": track["path"]}
        self._playlists_spotify = self.get_playlists_metadata(
            'local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "11_playlists__spotify_intial", **kwargs)

        # update Spotify playlists
        self.update_playlists(self._playlists_local, **kwargs)

    def report(self, **kwargs) -> None:
        if self._playlists_local is None:
            # get local metadata for m3u playlists
            self._verbose = True
            self._playlists_local = self.get_m3u_metadata(**kwargs)
            self.save_json(self._playlists_local, "10_playlists__local", **kwargs)

        uri_list = [track['uri'] for tracks in self._playlists_local.values()
                    for track in tracks if isinstance(track['uri'], str)]
        add_extra = {}
        for tracks in self._playlists_local.values():
            for track in tracks:
                if track['uri'] in uri_list:
                    add_extra[track['uri']] = {"folder": track["folder"], "path": track["path"]}
        # reload metadata and report
        self._playlists_spotify = self.get_playlists_metadata(
            'local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "12_playlists__spotify_final", **kwargs)
        playlist_uri = self.convert_metadata(
            self._playlists_spotify, key="name", value="uri", **kwargs)
        self.save_json(playlist_uri, "URIs__spotify_playlists", **kwargs)
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
        if start < 9:
            self.update_tags(quickload, **kwargs)  # Steps 7-9
            quickload = False
        if start < 12:
            self.update_spotify(quickload, **kwargs)  # Steps 10-12
            self.report(**kwargs)  # Step 13
            quickload = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync your local library to Spotify.", prog="syncify",
        usage='%(prog)s [function] [options]')
    parser._positionals.title = 'Functions'
    parser._optionals.title = 'Optional arguments'

    # cli function aliases and expected args in order user should give them
    functions = {
        "main": {"main": []},
        # individual main steps
        'check': {'check': []},
        'search': {'search': []},
        'update_tags': {'update_tags': []},
        'update_spotify': {'update_spotify': []},
        # reports/maintenance/utilities
        'report': {'report': []},
        'missing_tags': {'missing_tags': []},
        'backup': {'backup': []},
        'restore': {'restore': ['kind', 'playlists']},
        'extract': {'extract': ['kind', 'playlists']},
        "clean": {"clean_up_env": ['days', 'keep']},
        # endpoints
        "create": {"create_playlist": ['playlist_name', 'public', 'collaborative']},
        "get": {"get_data": ['name']},
        "delete": {"delete_playlist": ['playlist']},
        "clear": {"clear_from_playlist": ['playlist']},
    }
    parser.add_argument('function', nargs='?', default="main", choices=list(functions.keys()),
                        help=f"Syncify function to run.")

    local = parser.add_argument_group("Local library filters and options")
    local.add_argument('-q', '--quickload', required=False, nargs='?', default=False, const=True,
                       help="Skip load and search to use last run's load and search output. Enter a date to define which run to load from.")
    local.add_argument('-s', '--start', type=str, required=False, nargs='*', dest='prefix_start', metavar='',
                       help='Start processing from the folder with this prefix i.e. <folder>:<END>')
    local.add_argument('-e', '--end', type=str, required=False, nargs='*', dest='prefix_stop', metavar='',
                       help='Stop processing from the folder with this prefix i.e. <START>:<folder>')
    local.add_argument('-l', '--limit', type=str, required=False, nargs='*', dest='prefix_limit', metavar='',
                       help="Only process albums that start with this prefix")
    local.add_argument('-c', '--compilation', action='store_const', const=True,
                       help="Only process albums that are compilations")

    spotify = parser.add_argument_group("Spotify metadata extraction options")
    spotify.add_argument('-ag', '--add-genre', action='store_true',
                         help="Get genres when extracting track metadata from Spotify")
    spotify.add_argument('-af', '--add-features', action='store_true',
                         help="Get audio features when extracting track metadata from Spotify")
    spotify.add_argument('-aa', '--add-analysis', action='store_true',
                         help="Get audio analysis when extracting track metadata from Spotify (long runtime)")
    spotify.add_argument('-ar', '--add-raw', action='store_true',
                         help="Keep raw API data back when extracting track metadata from Spotify")

    playlists = parser.add_argument_group("Playlist processing options")
    playlists.add_argument('-in', '--in-playlists', required=False, nargs='*', metavar='',
                           help=f"Playlist names to include in any playlist processing")
    playlists.add_argument('-ex', '--ex-playlists', required=False, nargs='*', metavar='',
                           help=f"Playlist names to exclude in any playlist processing")
    playlists.add_argument('-f', '--filter', required=False, nargs='?', dest='filter_tags', default=False, const='filter',
                           help="Before updating Spotify playlists, filter out tracks with these tag values. Loads values from json file.")
    playlists.add_argument('-ce', '--clear-extra', action='store_const', dest='clear', default=False, const='extra',
                           help="Clear songs not present locally first when updating current Spotify playlists")
    playlists.add_argument('-ca', '--clear-all', action='store_const', dest='clear', default=False, const='all',
                           help="Clear all songs first when updating current Spotify playlists")

    tags = parser.add_argument_group("Local library tag update options")
    tag_options = list(LocalIO._tag_ids['.flac'].keys()) + ["uri"]
    tags.add_argument('-t', '--tags', required=False, nargs='*', metavar='',
                      choices=tag_options,
                      help=f"List of tags to update from Spotify to local files' metadata. Allowed values: {', '.join(tag_options)}.")
    tags.add_argument('-r', '--replace', action='store_true',
                      help="If set, destructively replace tags when updating local file tags")

    runtime = parser.add_argument_group("Runtime options")
    runtime.add_argument('-o', '--no-output', action='store_true',
                         help="Suppress all json file output, apart from files saved to the parent folder i.e. API token file and URIs.json")
    runtime.add_argument('-v', '--verbose', action='store_true',
                         help="Add additional stats on library to output throughout the run")
    runtime.add_argument('-x', '--execute', action='store_false', dest='dry_run',
                         help="Modify users files and playlist. Otherwise, do not affect files and append '_dry' to data folder path.")

    parsed_args = parser.parse_known_args()
    kwargs = vars(parsed_args[0])
    args = parsed_args[1]

    main = Syncify(verbose=kwargs['verbose'], auth=True, dry_run=kwargs["dry_run"])
    main.convert_kwargs(functions, args, kwargs)
    main._logger.debug(f"Args parsed: {args}")
    main._logger.debug(f"Kwargs parsed: \n{json.dumps(kwargs, indent=2)}")

    try:  # run the function requested by the user
        print()
        main._logger.info(f"\33[95mBegin running \33[1;95m{kwargs['function']}\33[0;95m function \33[0m")
        main._logger.info(f"\33[90mLogs output: {main._log_file} \33[0m")
        main._logger.info(f"\33[90mData output: {main.DATA_PATH} \33[0m")

        func = list(functions[kwargs["function"]].keys())[0]
        getattr(main, func)(**kwargs)
    except BaseException:
        main._logger.critical(traceback.format_exc())

    print()
    seconds = perf_counter() - main._start_time
    main._logger.info(
        f"\33[95mSyncified in {int(seconds // 60)} mins {int(seconds % 60)} secs \33[0m")
    main._logger.info(f"\33[90mLogs output: {main._log_file} \33[0m")
    main._logger.info(f"\33[90mData output: {main.DATA_PATH} \33[0m")

# TODO: Update readme
# TODO: track audio recognition when searching using Shazam like service?
# TODO: Automatically add songs added to each Spotify playlist to '2get'?
#       Then somehow update local library playlists after...
#       Maybe add a final step that syncs Spotify back to library if 
#       uris for extra songs in Spotify playlists found in library
