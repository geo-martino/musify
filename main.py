import json
import os
import re
import shutil
import traceback
from datetime import datetime as dt
from glob import glob
from os.path import basename, dirname, isdir, join
from time import perf_counter

from dateutil.relativedelta import relativedelta

from syncify.local.playlists import Playlists
from syncify.spotify.spotify import Spotify
from syncify.utils.authorise import ApiAuthoriser
from syncify.utils.environment import Environment
from syncify.utils.io import IO
from syncify.utils.logger import Logger
from syncify.utils.report import Report


class Syncify(Logger, ApiAuthoriser, IO, Report, Spotify, Playlists):

    extra_spotify_fields = [
        "uri", 
        "path", 
        "folder", 
        "filename", 
        "ext", 
        "date_modified", 
        "date_added", 
        "last_played", 
        "play_count",
        ]

    def __init__(
        self, 
        base_api: str, 
        open_url: str, 
        data_path: str, 
        music_path: str, 
        playlists_path: str, 
        spotify_api: dict, 
        kwargs: dict,
        android: dict = None, 
        musicbee_path: str = None, 
        other_paths: list = None, 
        verbose: int = 0,
        func: str = None,
        **other
        ) -> None:

        self._verbose = verbose
        self._dry_run = True
        self._headers = None
        self._start_time = perf_counter()  # for measuring total runtime

        self._verbose = verbose
        self._dry_run = kwargs.get("dry_run", self._dry_run)
        self._headers = None

        # set up logging and attributes from environment
        self._output_name = dt.strftime(dt.now(), '%Y-%m-%d_%H.%M.%S')
        if self._dry_run:
            self._output_name += "_dry"
        Logger.__init__(self)
        self._get_logger()

        if func:
            self._data_path = join(data_path, f"{self._output_name}_{func}")
            self.run = getattr(self, func)
        else:
            self._data_path = join(data_path, self._output_name)
            self.run = None

        self._base_api = base_api
        self._open_url = open_url
        self._music_path = music_path
        self._playlists_path = playlists_path
        self._musicbee_path = musicbee_path
        self._other_paths = other_paths

        # instantiate objects
        ApiAuthoriser.__init__(self, **spotify_api)
        IO.__init__(self)
        Playlists.__init__(self)
        Report.__init__(self)
        Spotify.__init__(self)

        # metadata placeholders
        self._library_local = None
        self._library_spotify = None
        self._playlists_local = None
        self._playlists_spotify = None

        self._logger.debug(f"Kwargs parsed: \n{json.dumps(kwargs, indent=2)}")


    def clean_up_env(self, days: int = 60, keep: int = 30, **kwargs) -> None:
        """
        Clears files older than {days} months and only keeps {keep} # of runs

        :param days: int, default=60. Age of files in months to keep.
        :param keep: int, default=30. Number of files to keep.
        """
        
        log = dirname(self._log_file)
        data = dirname(self._data_path)
        current_log = os.listdir(log)
        current_data = [basename(d) for d in glob(join(data, "*")) if isdir(d)]
        remove = []

        self._logger.debug(
            f"Log files: {len(current_log)} | "
            f"Data folders: {len(current_data)} | "
            f"Keep: {keep} | Days: {days}")

        remaining = len(current_data)
        for folder in sorted(current_data):  # clean up data
            if not re.match("\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}.*", folder):
                continue
            folder_dt = dt.strptime(folder[:19], "%Y-%m-%d_%H.%M.%S")
            dt_diff = folder_dt < dt.now() - relativedelta(days=days)
            path = join(data, folder)

            if path == self._data_path:  # skip current
                continue
            elif not os.listdir(path) or remaining >= keep or dt_diff:
                # empty folder or too many or too old
                remove.append(path)
                remaining -= 1
        
        remaining = len(current_log)
        for file in sorted(current_log):  # clean up logs
            if not re.match("\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}.*", file):
                continue
            file_dt = dt.strptime(file[:19], "%Y-%m-%d_%H.%M.%S")
            dt_diff = file_dt < dt.now() - relativedelta(days=days)
            path = join(log, file)

            if path == self._log_file:  # skip current
                continue
            elif file[:19] not in [f[:19] for f in current_data] or remaining >= keep or dt_diff:
                # orphaned log or too many or too old
                remove.append(path)
                remaining -= 1

        for path in remove:
            self._logger.debug(f"Removing {path}")
            shutil.rmtree(path) if isdir(path) else os.remove(path)
                

    def get_data(self, name: str, **kwargs) -> None:
        """Get tracks from Spotify for a given name/URI/URL/ID"""
        if self._headers is None:
            self._headers = self.auth()

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

    ###########################################################################
    ## Backup/Restore
    ###########################################################################
    def backup(self, **kwargs) -> None:
        """Backup all URI lists for local files/playlists and Spotify playlists"""
        if self._headers is None:
            self._headers = self.auth()
        
        # backup local library
        self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "backup__local_library", **kwargs)
        path_uri = self.convert_metadata(self._library_local, key="path", fields="uri", sort_keys=True, **kwargs)
        self.save_json(path_uri, "backup__local_library_URIs", **kwargs)

        # backup playlists and lists of tracks per playlist
        shutil.copytree(self._playlists_path, join(self._data_path, "backup__local_playlists"))
        self._playlists_local = self.get_local_playlists_metadata(tracks=library_path_metadata, **kwargs)
        self.save_json(self._playlists_local, "backup__local_playlists", **kwargs)

        # backup list of tracks per Spotify playlist
        add_extra = self.convert_metadata(self._library_local, key=None, fields=self.extra_spotify_fields, **kwargs)
        add_extra = [track for track in add_extra if isinstance(track['uri'], str)]
        self._playlists_spotify = self.get_playlists_metadata('local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "backup__spotify_playlists", **kwargs)

    def restore(self, quickload: str, kind: str, mod: str=None, **kwargs) -> None:
        """Restore  URI lists for local files/playlists and Spotify playlists
        
        :param kind: str. Restore 'local' or 'spotify'.
        :param mod: str, default=None. If kind='local', restore 'playlists' from syncify.local or restore playlists from 'spotify'
        """
        if not quickload:
            self._logger.warning("\n\33[91mSet a date to restore from using the quickload arg\33[0m")
            return

        if kind == "local":
            if not mod:  # local URIs
                self._library_local = self.load_local_metadata(**kwargs)
                library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
                self.enrich_metadata(library_path_metadata)
                self.save_json(self._library_local, "01_library__initial", **kwargs)
                self.restore_local_uris(self._library_local, f"{quickload}/backup__local_library_URIs", **kwargs)
            elif mod.lower().startswith("playlist"):
                self.restore_local_playlists(f"{quickload}/backup__local_playlists", **kwargs)
            elif mod.lower().startswith("spotify"):
                self.restore_local_playlists(f"{quickload}/backup__spotify_playlists", **kwargs)
        else:  # spotify playlists
            if self._headers is None:
                self._headers = self.auth()
            self.restore_spotify_playlists(f"{quickload}/backup__spotify_playlists", **kwargs)
    
    ###########################################################################
    ## Utilities/Misc.
    ###########################################################################
    def missing_tags(self, **kwargs) -> None:
        """Produces report on local tracks with defined set of missing tags"""

        # loads filtered library if filtering given, entire library if not
        self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "01_library__initial", **kwargs)

        missing_tags = self.report_missing_tags(self._library_local, **kwargs)
        self.save_json(missing_tags, "14_library__missing_tags", **kwargs)

    def extract(self, kind: str, playlists: bool = False, **kwargs):
        """Extract and save images from syncify.local files or Spotify"""

        self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)

        extract = []
        if kind == 'local':
            if not playlists:  # extract from entire local library
                self.save_json(self._library_local, "01_library__initial", **kwargs)
            else:  # extract from syncify.local playlists
                self._playlists_local = self.get_local_playlists_metadata(tracks=library_path_metadata, **kwargs)
                self.save_json(extract, "10_playlists__local", **kwargs)
        elif kind == 'spotify':
            if self._headers is None:
                self._headers = self.auth()
            if not playlists:  # extract from Spotify for entire library
                extract = self._extract_all_from_spotify(**kwargs)
                local = self.convert_metadata(self._library_local, key="uri", fields="track", **kwargs)

                for tracks in extract.values():
                    for track in tracks:
                        track["position"] = local[track["uri"]]
            else:  # extract from Spotify playlists
                extract = self.get_playlists_metadata('local', **kwargs)
                self.save_json(extract, "11_playlists__spotify_intial", **kwargs)
        
        self.extract_images(extract, True)
    
    def sync(self, **kwargs) -> None:
        """Synchrionise local playlists with external"""
        self.clean_playlists()

        self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "09_library__final", **kwargs)

        self._playlists_local = self.get_local_playlists_metadata(tracks=library_path_metadata, **kwargs)
        self.save_json(self._playlists_local, "10_playlists__local", **kwargs)

        self.compare_playlists(self._playlists_local, **kwargs) 

    def check(self, **kwargs) -> None:
        """Run check on entire library and update stored URIs tags"""
        if self._headers is None:
            self._headers = self.auth()

        # loads filtered library if filtering given, entire library if not
        self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "01_library__initial", **kwargs)
        path_uri = self.convert_metadata(self._library_local, key="path", fields="uri", sort_keys=True, **kwargs)
        self.save_json(path_uri, "URIs_initial", **kwargs)

        self.check_tracks(self._library_local, report_file="04_report__updated_uris", **kwargs)
        self.save_json(self._library_local, "05_report__check_matches", **kwargs)
        self.save_json(self._library_local, "06_library__checked", **kwargs)

        kwargs['tags'] = ['uri']
        self.update_file_tags(self._library_local, **kwargs)

        # create backup of new URIs
        path_uri = self.convert_metadata(self._library_local, key="path", fields="uri", sort_keys=True, **kwargs)
        self.save_json(path_uri, "URIs", **kwargs)
        self.save_json(path_uri, "URIs", parent=True, **kwargs)



    ###########################################################################
    ## Main runtime functions
    ###########################################################################
    def search(self, quickload, **kwargs) -> None:
        """Run all main steps up to search and check

        :param quickload: str, default=None. Date string. If set, load files from the
            folder with the given date.
        """
        if self._headers is None:
            self._headers = self.auth()
        
        ###########################################################################
        ## Step 1: LOAD LOCAL METADATA FOR LIBRARY
        ###########################################################################
        if quickload:  # load results from last search
            self._library_local = self.load_json(
                f"{quickload}/03_library__searched", parent=True, **kwargs)
        if not self._library_local:
            # loads filtered library if filtering given, entire library if not
            self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "01_library__initial", **kwargs)

        # create backup of current URIs
        path_uri = self.convert_metadata(self._library_local, key="path", fields="uri", sort_keys=True, **kwargs)
        self.save_json(path_uri, "URIs_initial", **kwargs)

        ###########################################################################
        ## Step 2-6: SEARCH/CHECK LIBRARY
        ###########################################################################
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
        matched = self.convert_metadata(search_results.get("matched", []), key="path", fields="uri", **kwargs)
        unmatched = self.convert_metadata(search_results.get("unmatched", []), key="path", fields="uri", **kwargs)
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
        if self._headers is None:
            self._headers = self.auth()

        if quickload:
            self._library_local = self.load_json(f"{quickload}/06_library__checked", parent=True, **kwargs)
        if not self._library_local:  # preload if needed
            # loads filtered library if filtering given, entire library if not
            self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "01_library__initial", **kwargs)

        ###########################################################################
        ## Step 7: LOAD SPOTIFY METADATA FOR ALL TRACKS/PLAYLISTS
        ###########################################################################
        # extract URI list and get Spotify metadata for all tracks with URIs in local library
        add_extra = self.convert_metadata(self._library_local, key=None, fields=self.extra_spotify_fields, **kwargs)
        add_extra = [track for track in add_extra if isinstance(track['uri'], str)]
        uri_list = [metadata['uri'] for metadata in add_extra]
        self._library_spotify = self.get_tracks_metadata(uri_list, add_extra=add_extra, **kwargs)

        self.save_json(self._library_spotify, '07_spotify__library', **kwargs)

    def update_tags(self, quickload, **kwargs) -> None:
        """Run all main functions for updating local files"""
        if self._headers is None:
            self._headers = self.auth()
        
        if kwargs['tags'] is None:
            self._logger.debug(f"\33[93mNo tags set by the user.")
            return

        if quickload:
            self._library_local = self.load_json(f"{quickload}/06_library__checked", parent=True, **kwargs)
            self._library_spotify = self.load_json(f"{quickload}/07_spotify__library", parent=True, **kwargs)
        if not self._library_local or not self._library_spotify:  # load if needed
            self._extract_all_from_spotify(False, **kwargs)

        ###########################################################################
        ## Step 8-9: TRANSFORM LOCAL TRACK METADATA, RELOAD LIBRARY
        ###########################################################################
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
        self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "09_library__final", **kwargs)

        # create backup of new URIs
        path_uri = self.convert_metadata(self._library_local, key="path", fields="uri", sort_keys=True, **kwargs)
        self.save_json(path_uri, "URIs", parent=True, **kwargs)

    def update_spotify(self, quickload, **kwargs) -> None:
        """Run all main functions for updating Spotify playlists"""
        if self._headers is None:
            self._headers = self.auth()

        if quickload:
            self._library_local = self.load_json(f"{quickload}/09_library__final", parent=True, **kwargs)
        if not self._library_local:  # load if needed
            self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "09_library__final", **kwargs)

        # get local metadata for m3u playlists
        self._playlists_local = self.get_local_playlists_metadata(tracks=library_path_metadata, **kwargs)
        self.save_json(self._playlists_local, "10_playlists__local", **kwargs)
        local_uri = self.convert_metadata(self._playlists_local, key="name", fields="uri", sort_keys=True, **kwargs)
        self.save_json(local_uri, "URIs__local_playlists", **kwargs)

        add_extra = self.convert_metadata(self._library_local, key=None, fields=self.extra_spotify_fields, **kwargs)
        add_extra = [track for track in add_extra if isinstance(track['uri'], str)]
        self._playlists_spotify = self.get_playlists_metadata(
            'local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "11_playlists__spotify_intial", **kwargs)

        # update Spotify playlists
        self.update_playlists(self._playlists_local, **kwargs)
        self.report(False, **kwargs)

    def report(self, quickload, **kwargs) -> None:
        if self._headers is None:
            self._headers = self.auth()
        
        if quickload:
            self._library_local = self.load_json(f"{quickload}/09_library__final", parent=True, **kwargs)
        if not self._library_local:  # load if needed
            self._library_local = self.load_local_metadata(**kwargs)
        library_path_metadata = self.convert_metadata(self._library_local, key="path", **kwargs)
        self.enrich_metadata(library_path_metadata)
        self.save_json(self._library_local, "09_library__final", **kwargs)

        if self._playlists_local is None:  # get local metadata for m3u playlists
            self._playlists_local = self.get_local_playlists_metadata(tracks=library_path_metadata, **kwargs)
            self.save_json(self._playlists_local, "10_playlists__local", **kwargs)
        
        # reload metadata and report
        add_extra = self.convert_metadata(self._library_local, key=None, fields=self.extra_spotify_fields, **kwargs)
        add_extra = [track for track in add_extra if isinstance(track['uri'], str)]
        self._playlists_spotify = self.get_playlists_metadata(
            'local', add_extra=add_extra, **kwargs)
        self.save_json(self._playlists_spotify, "12_playlists__spotify_final", **kwargs)
        playlist_uri = self.convert_metadata(
            self._playlists_spotify, key="name", fields="uri", sort_keys=True, **kwargs)
        self.save_json(playlist_uri, "URIs__spotify_playlists", **kwargs)
        self._verbose = self._verbose if self._verbose > 0 else 1
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
            files = glob(join(dirname(self._data_path), quickload, "*"))
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

if __name__ == "__main__":
    env = Environment()
    env.get_kwargs()
    env.parse_from_bash()
    
    for func, settings in env.runtime_settings.items():
        print()
        try:  # run the functions requested by the user
            main = Syncify(func=func, **settings)
            main._logger.info(f"\33[95mBegin running \33[1;95m{func}\33[0;95m function \33[0m")
            main._logger.info(f"\33[90mLogs output: {main._log_file} \33[0m")
            main._logger.info(f"\33[90mData output: {main._data_path} \33[0m")
            main.run(**settings["kwargs"])
            main._close_handlers()         
        except BaseException:
            main._logger.critical(traceback.format_exc())
            break

        main._logger.info(f"\33[95m\33[1;95m{func}\33[0;95m complete\33[0m")
        main._logger.info(f"\33[90mLogs output: {main._log_file} \33[0m")
        main._logger.info(f"\33[90mData output: {main._data_path} \33[0m")

    print()
    seconds = perf_counter() - main._start_time
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    main._logger.info( f"\33[95mSyncified in {mins} mins {secs} secs \33[0m")

# TODO: track audio recognition when searching using Shazam like service?
# TODO: Automatically add songs added to each Spotify playlist to '2get'?
#  Then somehow update local library playlists after...
#  Maybe add a final step that syncs Spotify back to library if
#  uris for extra songs in Spotify playlists found in library
# TODO: function to open search website tabs for all songs in 2get playlist
#  on common music stores/torrent sites
# TODO: get_items returns 100 items and it's messing up the items extension parts of input responses?
