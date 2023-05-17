import json
import os
import re
import shutil
import traceback
from copy import copy
from datetime import datetime as dt
from glob import glob
from os.path import basename, dirname, isdir, join
from time import perf_counter
from typing import List, Optional, Mapping, Any, Callable

from dateutil.relativedelta import relativedelta

from syncify.abstract.collection import BasicCollection
from syncify.spotify.processor import Searcher, Checker
from syncify.spotify.processor.search import Algorithm, AlgorithmSettings
from syncify.local.library import LocalLibrary, MusicBee
from syncify.spotify.library import SpotifyLibrary
from syncify.settings import Settings
from syncify.report import Report
from syncify.spotify.api import API
from syncify.utils.logger import Logger


class Syncify(Settings, Report):

    allowed_functions = ["clean_up_env", "search"]

    @property
    def time_taken(self) -> float:
        return perf_counter() - self._start_time

    @property
    def api(self) -> API:
        if self._api is None:
            self._api = API(**self.cfg_run["spotify"]["api"]["settings"])
        return self._api

    @property
    def local_library(self) -> LocalLibrary:
        if self._local_library is None:
            library_folder = self.cfg_run["local"]["paths"].get("library")
            musicbee_folder = self.cfg_run["local"]["paths"].get("musicbee")
            playlist_folder = self.cfg_run["local"]["paths"].get("playlist")
            other_folders = self.cfg_run["local"]["paths"].get("other")
            include = self.cfg_run["local"].get("playlists", {}).get("include")
            exclude = self.cfg_run["local"].get("playlists", {}).get("exclude")

            if musicbee_folder:
                self._local_library = MusicBee(library_folder=library_folder, musicbee_folder=musicbee_folder,
                                               other_folders=other_folders, include=include, exclude=exclude)
            else:
                self._local_library = LocalLibrary(library_folder=library_folder, playlist_folder=playlist_folder,
                                                   other_folders=other_folders, include=include, exclude=exclude)
        return self._local_library

    @property
    def spotify_library(self) -> SpotifyLibrary:
        if self._spotify_library is None:
            use_cache = self.cfg_run["spotify"]["api"].get("use_cache", True)
            include = self.cfg_run["spotify"].get("playlists", {}).get("include")
            exclude = self.cfg_run["spotify"].get("playlists", {}).get("exclude")

            self._spotify_library = SpotifyLibrary(api=self.api, include=include, exclude=exclude, use_cache=use_cache)
        return self._spotify_library

    def __init__(self, config_path: str = "config.yml"):
        self._start_time = perf_counter()  # for measuring total runtime
        Settings.__init__(self, config_path=config_path)
        Logger.__init__(self)

        self.run: Optional[Callable] = None
        self.cfg_run: Mapping[Any, Any] = self.cfg_general

        self._api: Optional[API] = None
        self._local_library: Optional[LocalLibrary] = None
        self._android_library: Optional[LocalLibrary] = None
        self._spotify_library: Optional[SpotifyLibrary] = None

        self.logger.debug(f"Initialisation of Syncify object: DONE\n")

    def set_func(self, name: str):
        self.run = getattr(self, name)
        self.cfg_run = self.cfg_functions.get(name, self.cfg_general)

    def clean_up_env(self) -> None:
        """Clears files older than a number of days and only keeps max # of runs"""
        days = self.cfg_general["cleanup"]["days"]
        runs = self.cfg_general["cleanup"]["runs"]

        logs = dirname(self.log_folder)
        output = dirname(self.output_folder)
        current_logs = [d for d in glob(join(logs, "*")) if isdir(d) and d != self.log_path]
        current_output = [d for d in glob(join(output, "*")) if isdir(d) and d != self.output_folder]

        self.logger.debug(f"Log folders: {len(current_logs)} | Output folders: {len(current_output)} | "
                          f"Days: {days} | Runs: {runs}")

        remove = []
        dates = []

        def get_paths_to_remove(paths: List[str]):
            remaining = len(paths) + 1

            for path in sorted(paths):
                folder = basename(path)
                if not re.match(r"\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}.*", folder):
                    continue
                folder_dt = dt.strptime(folder[:19], self.dt_format)
                dt_diff = folder_dt < dt.now() - relativedelta(days=days)

                # empty folder or too many or too old or date set to be removed
                if not os.listdir(path) or remaining >= runs or dt_diff or folder_dt in dates:
                    remove.append(path)
                    dates.append(folder_dt)
                    remaining -= 1

        get_paths_to_remove(current_output)
        get_paths_to_remove(current_logs)

        for p in remove:
            self.logger.debug(f"Removing {p}")
            shutil.rmtree(p)

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
            self.logger.warning("\n\33[91mSet a date to restore from using the quickload arg\33[0m")
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
    def search(self) -> None:
        """Run all methods for searching and checking URI associations with local files"""
        if len([track for track in self.local_library.tracks if track.has_uri is None]) == 0:
            self.logger.info("All songs found or unavailable. Skipping search.")
            return

        collections = [BasicCollection(folder.name, [track for track in folder if track.has_uri is None])
                       for folder in self.local_library.folders
                       if any(track.has_uri is None for track in folder)]
        cfg = self.cfg_run["spotify"]

        algorithm: Algorithm = cfg.get("search", {}).get("algorithm", AlgorithmSettings.FULL)
        searcher = Searcher(api=self.api, algorithm=algorithm)
        searcher.search(collections)

        checker = Checker(self.api, allow_karaoke=algorithm.allow_karaoke)
        checker.check(collections, interval=cfg.get("check", {}).get("interval", 10))

    def update_tags(self, quickload, **kwargs) -> None:
        """Run all main functions for updating local files"""

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
    main = Syncify()
    # env.get_kwargs()
    main.parse_from_prompt()
    
    for func in main.functions:
        print()
        try:  # run the functions requested by the user
            main.set_func(func)
            main.logger.info(f"\33[95mBegin running \33[1;95m{func}\33[0;95m function \33[0m")
            main.logger.info(f"\33[90mLogs: {main.log_path} \33[0m")
            main.logger.info(f"\33[90mOutput: {main.output_folder} \33[0m")
            main.run()
            # main._close_handlers()
        except BaseException:
            main.logger.critical(traceback.format_exc())
            break

        main.logger.info(f"\33[95m\33[1;95m{func}\33[0;95m complete\33[0m")
        main.logger.info(f"\33[90mLogs: {main.log_path} \33[0m")
        main.logger.info(f"\33[90mOutput: {main.output_folder} \33[0m")

    print()
    seconds = main.time_taken
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    main.logger.info( f"\33[95mSyncified in {mins} mins {secs} secs \33[0m")

# TODO: track audio recognition when searching using Shazam like service?
# TODO: Automatically add songs added to each Spotify playlist to '2get'?
#  Then somehow update local library playlists after...
#  Maybe add a final step that syncs Spotify back to library if
#  uris for extra songs in Spotify playlists found in library
# TODO: function to open search website tabs for all songs in 2get playlist
#  on common music stores/torrent sites
# TODO: get_items returns 100 items and it's messing up the items extension parts of input responses?
