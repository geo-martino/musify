import json
import os
import re
import shutil
import sys
import traceback
from collections.abc import Callable, Mapping, Collection
from datetime import datetime as dt
from glob import glob
from os.path import basename, dirname, isdir, join, relpath
from time import perf_counter
from typing import Any

from dateutil.relativedelta import relativedelta

from syncify import PROGRAM_NAME
from syncify.config import REMOTE_CONFIG
from syncify.exception import SyncifyError
from syncify.fields import LocalTrackField
from syncify.local.collection import LocalFolder
from syncify.local.library import LocalLibrary, MusicBee
from syncify.remote.api.api import RemoteAPI
from syncify.remote.config import RemoteClasses
from syncify.remote.library.library import RemoteLibrary
from syncify.remote.processors.search import AlgorithmSettings
from syncify.report import Report
from syncify.settings import Settings
from syncify.utils.helpers import get_user_input
from syncify.utils.logger import STAT
from syncify.utils.printers import print_logo, print_line, print_time


class Syncify(Settings, Report):
    """
    Core functionality and meta-functions for the program

    :param config_path: Path of the config file to use.
    """

    @property
    def allowed_functions(self) -> list[str]:
        return [
            method for method, value in Syncify.__dict__.items()
            if not method.startswith('_') and callable(value) and method not in [self.set_func.__name__]
        ]

    @property
    def time_taken(self) -> float:
        """The total time taken since initialisation"""
        return perf_counter() - self._start_time

    @property
    def remote_source(self) -> str | None:
        """Remote source name setting according to current config"""
        return self.cfg_run.get("remote", {}).get("source")

    @property
    def remote_config(self) -> RemoteClasses:
        """Remote source config to current remote source name"""
        return REMOTE_CONFIG[self.remote_source.casefold().strip()]

    @property
    def api(self) -> RemoteAPI:
        """Set the API if not already set and return"""
        if self._api is None:
            self.logger.info(f"\33[1;95m ->\33[1;97m Authorising API access \33[0m")
            self._api = self.remote_config.api(**self.cfg_run[self.remote_source]["api"]["settings"])
            self.remote_config.object.api = self._api
            self.print_line()
        return self._api

    @property
    def use_cache(self) -> bool:
        """``use_cache`` setting according to current config"""
        return self.cfg_run.get(self.remote_source, {}).get("api", {}).get("use_cache", True)

    @property
    def local_library(self) -> LocalLibrary:
        """Set the LocalLibrary if not already set and return"""
        if self._local_library is None:
            library_folder = self.cfg_run["local"]["paths"].get("library")
            musicbee_folder = self.cfg_run["local"]["paths"].get("musicbee")
            playlist_folder = self.cfg_run["local"]["paths"].get("playlist")
            other_folders = self.cfg_run["local"]["paths"].get("other")
            include = self.cfg_run["local"].get("playlists", {}).get("include")
            exclude = self.cfg_run["local"].get("playlists", {}).get("exclude")

            if musicbee_folder:
                self._local_library = MusicBee(
                    library_folder=library_folder,
                    musicbee_folder=musicbee_folder,
                    other_folders=other_folders,
                    include=include,
                    exclude=exclude,
                    remote_wrangler=self.remote_config.wrangler()
                )
            else:
                self._local_library = LocalLibrary(
                    library_folder=library_folder,
                    playlist_folder=playlist_folder,
                    other_folders=other_folders,
                    include=include,
                    exclude=exclude,
                    remote_wrangler=self.remote_config.wrangler()
                )

        return self._local_library

    @property
    def local_library_backup_name(self) -> str:
        """The filename to use for backups of the LocalLibrary"""
        return f"{self.local_library.__class__.__name__} - {self.local_library.name}"

    @property
    def remote_library(self) -> RemoteLibrary:
        """Set the RemoteLibrary if not already set and return"""
        if self._remote_library is None:
            use_cache = self.cfg_run[self.remote_source]["api"].get("use_cache", True)
            include = self.cfg_run[self.remote_source].get("playlists", {}).get("include")
            exclude = self.cfg_run[self.remote_source].get("playlists", {}).get("exclude")

            self._remote_library = self.remote_config.library(
                api=self.api, include=include, exclude=exclude, use_cache=use_cache
            )
        return self._remote_library

    @property
    def spotify_library_backup_name(self) -> str:
        """The filename to use for backups of the RemoteLibrary"""
        return f"{self.remote_library.__class__.__name__} - {self.remote_library.name}"

    def __init__(self, config_path: str = "config.yml"):
        self._start_time = perf_counter()  # for measuring total runtime
        super().__init__(config_path=config_path)

        self.run: Callable[[], Any] | None = None
        self.cfg_run: Mapping[Any, Any] = self.cfg_general

        if self.remote_source not in REMOTE_CONFIG:
            raise SyncifyError(f"Given remote source is not supported: {self.remote_source}")

        self._api: RemoteAPI | None = None
        self._local_library: LocalLibrary | None = None
        self._android_library: LocalLibrary | None = None
        self._remote_library: RemoteLibrary | None = None

        self.logger.debug(f"Initialisation of {PROGRAM_NAME} object: DONE\n")

    def set_func(self, name: str) -> None:
        """Set the current runtime function to call at ``self.run`` and set its config for this run"""
        self.run = getattr(self, name)
        self.cfg_run = self.cfg_functions.get(name, self.cfg_general)

    def _save_json(self, filename: str, data: Mapping[str, Any], folder: str | None = None) -> None:
        """Save a JSON file to a given folder, or this run's folder if not given"""
        if not filename.casefold().endswith(".json"):
            filename += ".json"
        folder = folder if folder else self.output_folder
        path = join(folder, filename)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_json(self, filename: str, folder: str | None = None) -> dict[str, Any]:
        """Load a stored JSON file from a given folder, or this run's folder if not given"""
        if not filename.casefold().endswith(".json"):
            filename += ".json"
        folder = folder if folder else self.output_folder
        path = join(folder, filename)

        with open(path, "r") as f:
            data = json.load(f)

        return data

    def _get_limited_folders(self) -> list[LocalFolder]:
        """Returns a limited set of local folders based on config conditions"""
        # get filter conditions
        include_prefix = self.cfg_run.get("filter", {}).get("include", {}).get("prefix", "").strip().casefold()
        exclude_prefix = self.cfg_run.get("filter", {}).get("exclude", {}).get("prefix", "").strip().casefold()
        start = self.cfg_run.get("filter", {}).get("start", "").strip().casefold()
        stop = self.cfg_run.get("filter", {}).get("stop", "").strip().casefold()

        folders = []
        for folder in self.local_library.folders:  # apply filter
            name = folder.name.strip().casefold()
            conditionals = {
                not include_prefix or name.startswith(include_prefix),
                not exclude_prefix or not name.startswith(exclude_prefix),
                not start or name >= start, not stop or name <= stop
            }
            if all(conditionals):
                folders.append(folder)

        return folders

    ###########################################################################
    ## Maintenance/Utilities
    ###########################################################################
    def pause(self) -> None:
        """Pause the program with a message and wait for user input to continue"""
        message = self.cfg_run.get("message", "Pausing, hit return to continue...").strip()
        input(f"\33[93m{message}\33[0m ")
        self.print_line()

    def reload(self) -> None:
        """Reload libraries if they are initialised"""
        self.logger.debug("Reload libraries: START")

        if self._local_library is not None:
            self.local_library.load(log=False)
        if self._remote_library is not None:
            self.remote_library.use_cache = self.use_cache
            self.remote_library.load(log=False)
            self.remote_library.extend(self.local_library)
            self.remote_library.enrich_tracks(artists=True)

        self.logger.debug("Reload libraries: DONE\n")

    def print_data(self) -> None:
        """Pretty print data from user's input"""
        self.api.pretty_print_uris(use_cache=self.use_cache)

    def clean_env(self) -> None:
        """Clears files older than a number of days and only keeps max # of runs"""
        self.logger.debug(f"Clean {PROGRAM_NAME} files: START")

        days = self.cfg_general["cleanup"]["days"]
        runs = self.cfg_general["cleanup"]["runs"]

        # get current folders present
        logs = dirname(self.log_folder)
        output = dirname(self.output_folder)
        current_logs = tuple(d for d in glob(join(logs, "*")) if isdir(d) and d != self.log_path)
        current_output = tuple(d for d in glob(join(output, "*")) if isdir(d) and d != self.output_folder)

        self.logger.debug(
            f"Log folders: {len(current_logs)} | Output folders: {len(current_output)} | "
            f"Days: {days} | Runs: {runs}"
        )

        remove = []
        dates = []

        def get_paths_to_remove(paths: Collection[str]) -> None:
            """Determine which folders to remove based on settings"""
            remaining = len(paths) + 1

            for path in sorted(paths):
                folder = basename(path)
                if not re.match(r"\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}.*", folder):
                    continue
                folder_dt = dt.strptime(folder[:19], self.dt_format)
                dt_diff = folder_dt < dt.now() - relativedelta(days=days)

                # empty folder or too many or too old or date set to be removed already
                if not os.listdir(path) or remaining >= runs or dt_diff or folder_dt in dates:
                    remove.append(path)
                    dates.append(folder_dt)
                    remaining -= 1

        get_paths_to_remove(current_logs)
        get_paths_to_remove(current_output)

        for p in remove:  # delete folders
            self.logger.debug(f"Removing {p}")
            shutil.rmtree(p)

        self.logger.info(f"\33[1;95m ->\33[1;92m Removed {len(remove)} folders\33[0m")
        self.print_line()
        self.logger.debug(f"Clean {PROGRAM_NAME} files: DONE\n")

    ###########################################################################
    ## Backup/Restore
    ###########################################################################
    def backup(self, is_final: bool = False) -> None:
        """Backup data for all tracks and playlists in all libraries"""
        self.logger.debug("Backup libraries: START")

        local_backup_name = self.local_library_backup_name
        local_backup_name = f"[FINAL] - {local_backup_name}" if is_final else local_backup_name
        self._save_json(local_backup_name, self.local_library.as_json())

        spotify_backup_name = self.spotify_library_backup_name
        spotify_backup_name = f"[FINAL] - {spotify_backup_name}" if is_final else spotify_backup_name
        self._save_json(spotify_backup_name, self.remote_library.as_json())
        self.logger.debug("Backup libraries: DONE\n")

    def restore(self) -> None:
        """Restore library data from a backup, getting user input for the settings"""
        output_parent = dirname(self.output_folder)
        backup_names = (self.local_library_backup_name, self.spotify_library_backup_name)
        available_backup_names = tuple(
            relpath(path[0], output_parent) for path in os.walk(output_parent)
            if path[0] != output_parent and any(any(name in file for name in backup_names) for file in path[2])
        )
        if len(available_backup_names) == 0:
            self.logger.info("\33[93mNo backups found, skipping.\33[0m")

        self.logger.info(
            "\33[97mAvailable backups: \n\t\33[97m- \33[94m{n}\33[0m"
            .format(n="\33[0m\n\t\33[97m-\33[0m \33[94m".join(available_backup_names))
        )

        while True:  # get valid user input
            restore_from = get_user_input("Select the backup to use")
            if restore_from in available_backup_names:  # input is valid
                break
            print(f"\33[91mBackup '{restore_from}' not recognised, try again\33[0m")
        restore_from = join(output_parent, restore_from)

        if get_user_input("Restore local library tracks? (enter 'y')").casefold() == 'y':
            self._restore_local(restore_from)
        if get_user_input(f"Restore {self.remote_source} library playlists? (enter 'y')").casefold() == 'y':
            self._restore_spotify(restore_from)

    def _restore_local(self, folder: str) -> None:
        """Restore local library data from a backup, getting user input for the settings"""
        self.logger.debug("Restore local: START")

        tags = LocalTrackField.ALL.to_tag()
        self.logger.info(f"\33[97mAvailable tags to restore: \33[94m{', '.join(tags)}\33[0m")
        message = "Select tags to restore separated by a space (entering nothing restores all available tags)"

        while True:  # get valid user input
            restore_tags = {t.casefold().strip() for t in get_user_input(message).split()}
            if not restore_tags:  # user entered nothing, restore all tags
                restore_tags = LocalTrackField.ALL.to_tag()
                break
            elif all(t in tags for t in restore_tags):  # input is valid
                break
            print(f"\33[91mTags entered were not recognised ({', '.join(restore_tags)}), try again\33[0m")

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Restoring local track tags from backup: "
            f"{basename(folder)} | Tags: {', '.join(restore_tags)}\33[0m"
        )
        self.print_line()
        backup = self._load_json(self.local_library_backup_name, folder)

        # restore and save
        self.local_library.restore_tracks(backup["tracks"], tags=LocalTrackField.from_name(*restore_tags))
        results = self.local_library.save_tracks(tags=tags, replace=True, dry_run=self.dry_run)

        self.local_library.log_save_tracks(results)
        self.logger.debug("Restore local: DONE\n")

    def _restore_spotify(self, folder: str) -> None:
        """Restore remote library data from a backup, getting user input for the settings"""
        self.logger.debug(f"Restore {self.remote_source}: START")

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Restoring {self.remote_source} playlists from backup: {basename(folder)} \33[0m"
        )
        self.print_line()
        backup = self._load_json(self.spotify_library_backup_name, folder)

        # restore and sync
        self.remote_library.restore_playlists(backup["playlists"])
        results = self.remote_library.sync(clear="all", reload=False, dry_run=False)
        self.remote_library.log_sync(results)

        self.logger.debug(f"Restore {self.remote_source}: DONE\n")

    def extract(self) -> None:
        """Extract and save images from local or remote items"""
        # TODO: add library-wide image extraction method
        raise NotImplementedError

    ###########################################################################
    ## Report/Search functions
    ###########################################################################
    def report(self) -> None:
        """Produce various reports on loaded data"""
        self.logger.debug("Generate reports: START")
        cfg = self.cfg_run.get("reports", {})
        if cfg.get("library_differences").get("enabled", True):
            self.report_library_differences(self.local_library, self.remote_library)
        if cfg.get("missing_tags").get("enabled", True):
            self.report_missing_tags(self.local_library.folders)
        self.logger.debug("Generate reports: DONE\n")

    def check(self) -> None:
        """Run check on entire library by album and update URI tags on file"""
        self.logger.debug("Check and update URIs: START")

        folders = self._get_limited_folders()

        allow_karaoke = AlgorithmSettings.ITEMS.allow_karaoke
        checker = self.remote_config.checker(api=self.api, allow_karaoke=allow_karaoke)
        check_results = checker.check(folders, interval=self.cfg_run.get("interval", 10))

        if check_results:
            self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local_library)} tracks: uri \33[0m")
            results = self.local_library.save_tracks(tags=LocalTrackField.URI, replace=True, dry_run=self.dry_run)

            if results:
                self.print_line(STAT)
            self.local_library.log_save_tracks(results)
            self.logger.info(f"\33[92m    Done | Set tags for {len(results)} tracks \33[0m")

        self.print_line()
        self.logger.debug("Check and update URIs: DONE\n")

    def search(self) -> None:
        """Run all methods for searching, checking, and saving URI associations for local files."""
        self.logger.debug("Search and match: START")

        albums = self.local_library.albums
        [album.items.remove(track) for album in albums for track in album.items.copy() if track.has_uri is not None]
        [albums.remove(album) for album in albums.copy() if len(album.items) == 0]

        if len(albums) == 0:
            self.logger.info("\33[1;95m ->\33[0;90m All items matched or unavailable. Skipping search.\33[0m")
            self.print_line()
            return

        allow_karaoke = AlgorithmSettings.ITEMS.allow_karaoke
        searcher = self.remote_config.searcher(api=self.api, allow_karaoke=allow_karaoke)
        searcher.search(albums)

        checker = self.remote_config.checker(api=self.api, allow_karaoke=allow_karaoke)
        checker.check(albums, interval=self.cfg_run.get("interval", 10))

        self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local_library)} tracks: uri \33[0m")
        results = self.local_library.save_tracks(tags=LocalTrackField.URI, replace=True, dry_run=self.dry_run)

        if results:
            self.print_line(STAT)
        self.local_library.log_save_tracks(results)
        self.logger.info(f"\33[92m    Done | Set tags for {len(results)} tracks \33[0m")
        self.print_line()
        self.logger.debug("Search and match: DONE\n")

    ###########################################################################
    ## Export from Syncify to sources
    ###########################################################################
    def get_tags(self) -> None:
        """Run all methods for synchronising local data with remote and updating local track tags"""
        self.logger.debug("Update tags: START")

        replace = self.cfg_run.get("local", {}).get("update", {}).get("replace", False)
        tag_names = self.cfg_run.get("local", {}).get("update", {}).get("tags")
        tags = LocalTrackField.ALL if not tag_names else LocalTrackField.from_name(*tag_names)

        # add extra local tracks to remote library and merge remote items to local library
        self.remote_library.extend(self.local_library)
        self._remote_library.enrich_tracks(artists=True)
        self.local_library.merge_items(self.remote_library, tags=tags)

        # save tags to files
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local_library)} tracks: "
            f"{', '.join(t.name.lower() for t in tags)} \33[0m"
        )
        results = self.local_library.save_tracks(tags=tags, replace=replace, dry_run=self.dry_run)

        if results:
            self.print_line(STAT)
        self.local_library.log_save_tracks(results)
        self.logger.info(f"\33[92m    Done | Set tags for {len(results)} tracks \33[0m")
        self.print_line()
        self.logger.debug("Update tags: DONE\n")

    def process_compilations(self) -> None:
        """Run all methods for setting and updating local track tags for compilation albums"""
        self.logger.debug("Update compilations: START")
        folders = self._get_limited_folders()

        # get settings
        replace = self.cfg_run.get("local", {}).get("update", {}).get("replace", False)
        tag_names = self.cfg_run.get("local", {}).get("update", {}).get("tags")
        tags = [LocalTrackField.ALL] if not tag_names else LocalTrackField.from_name(*tag_names)
        item_count = sum(len(folder) for folder in folders)

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Setting and saving compilation style tags "
            f"for {item_count} tracks in {len(folders)} folders: "
            f"{', '.join(t.name.lower() for t in tags)} \33[0m"
        )

        results = {}
        for folder in self.get_progress_bar(iterable=folders, desc="Setting tags", unit="folders"):  # set tags
            folder.set_compilation_tags()
            results |= folder.save_tracks(tags=tags, replace=replace, dry_run=self.dry_run)

        if results:
            self.print_line(STAT)
        self.local_library.log_save_tracks(results)
        self.logger.info(f"\33[92m    Done | Set tags for {len(results)} tracks \33[0m")
        self.print_line()
        self.logger.debug("Update compilations: Done\n")

    def sync_spotify(self) -> None:
        """Run all main functions for synchronising remote playlists with a local library"""
        self.logger.debug(f"Update {self.remote_source}: START")

        if self._local_library is not None:  # reload local library
            self.local_library.load(tracks=False, log=False)

        cfg_playlists = self.cfg_run.get("spotify", {}).get("playlists", {})

        filter_tags = cfg_playlists.get("sync", {}).get("filter", {})
        include = cfg_playlists.get("include")
        exclude = cfg_playlists.get("exclude")
        playlists = self.local_library.get_filtered_playlists(include=include, exclude=exclude, **filter_tags)

        # sync to remote
        clear = cfg_playlists.get("sync", {}).get("clear")
        reload = cfg_playlists.get("sync", {}).get("reload")
        results = self.remote_library.sync(playlists, clear=clear, reload=reload, dry_run=self.dry_run)
        self.remote_library.log_sync(results)

        self.logger.debug(f"Update {self.remote_source}: DONE\n")


if __name__ == "__main__":
    print_logo()
    main = Syncify()
    main.parse_from_prompt()
    main.logger.info(f"\33[90mLogs: {main.log_path} \33[0m")
    main.logger.info(f"\33[90mOutput: {main.output_folder} \33[0m")

    if main.dry_run:
        print_line("DRY RUN ENABLED", " ")

    failed = False
    for i, func in enumerate(main.functions, 1):
        title = f"{PROGRAM_NAME}: {func}"
        if main.dry_run:
            title += " (DRYRUN)"

        if sys.platform == "win32":
            os.system(f"title {title}")
        elif sys.platform == "linux" or sys.platform == "darwin":
            os.system(f"echo '\033]2;{title}\007'")

        # noinspection PyBroadException
        try:  # run the functions requested by the user
            main.logger.debug(f"START function: {func}")
            main.set_func(func)

            if main.run == main.backup and i == len(main.functions):
                print_line(f"final_{func}")
                main.backup(True)
            else:
                print_line(func)
                main.run()

            main.logger.debug(f"DONE  function: {func}")
        except BaseException:
            main.logger.critical(traceback.format_exc())
            failed = True
            break

    main.close_handlers()
    print_logo()
    print_time(main.time_taken)


## BIGGER ONES
# TODO: function to open search website tabs for all songs in 2get playlist
#  on common music stores/torrent sites
# TODO: Automatically add songs added to each remote playlist to '2get'?
#  Then somehow update local library playlists after...
#  Maybe add a final step that syncs remote back to library if
#  uris for extra songs in remote playlists found in library
# TODO: track audio recognition when searching using Shazam like service?
#  Maybe https://audd.io/ ?
# TODO: expand search/match functionality to include all item types
# TODO: new music playlist that adds songs from artists user follows that
#  have been released within a given timeframe e.g. a day
# TODO: implement XAutoPF full update functionality
# TODO: expand docstrings everywhere


## SMALLER/GENERAL ONES
# TODO: parallelize all the things
# TODO: generally improve performance
# TODO: look into the requests_cache, it grows way too big sometimes?
# TODO: implement terminal parser for function-specific kwargs?
# TODO: implement GitHub actions for testing builds + implement release structure


## SELECTED FOR DEVELOPMENT
# TODO: test on linux/mac
#  - concerned about local playlist saving
#  - linux does not pick up 'include' paths when loading xautopf playlists
#    this is possibly due to case-sensitive paths not being found in linux
#    from using lowercase path cleaning logic in TrackMatch
#  This may now be fixed by extending functionality of playlists to include
#   available track paths on load
# TODO: implement merge_playlists functions and,
#  by extension, implement android library sync
# TODO: improve separation of concerns for main and settings
#  settings object should contain all settings as properties to be accessed by main
#  main should never need to access the yaml dict config directly


## NEEDED FOR v0.3
# TODO: parse all string fields to quoted for MusicBee XML
# TODO: write tests to validate Field enum names are all present in related abstract classes
#  and write test to ensure all mapped fields are present in FieldCombined enum
# TODO: write tests, write tests, write tests
# TODO: update the readme (dynamic readme?)
# TODO: ensure all classes still print as expected
#  add tests for to_dict(), str() and repr() methods on all inheritors on PrettyPrinter
