import json
import logging
import os
import sys
import traceback
from collections.abc import Mapping
from os.path import basename, dirname, join, relpath, splitext
from time import perf_counter
from typing import Any, Callable

from syncify import PROGRAM_NAME
from syncify.config import Config, ConfigAPI, ConfigLibraryDifferences, ConfigMissingTags, ConfigRemote, ConfigLocal
from syncify.fields import LocalTrackField
from syncify.processors.base import DynamicProcessor, dynamicprocessormethod
from syncify.report import report_playlist_differences, report_missing_tags
from syncify.utils.helpers import get_user_input
from syncify.utils.logger import SyncifyLogger, STAT, CurrentTimeRotatingFileHandler
from syncify.utils.printers import print_logo, print_line, print_time


class Syncify(DynamicProcessor):
    """Core functionality and meta-functions for the program"""

    @property
    def time_taken(self) -> float:
        """The total time taken since initialisation"""
        return perf_counter() - self._start_time

    @property
    def local_source(self) -> str:
        """The name of the remote source currently being used"""
        return self.local.library.name

    @property
    def remote_source(self) -> str:
        """The name of the remote source currently being used"""
        return self.remote.library.remote_source

    def __init__(self, config: Config, local: str, remote: str):
        self._start_time = perf_counter()  # for measuring total runtime
        # noinspection PyTypeChecker
        self.logger: SyncifyLogger = logging.getLogger(__name__)
        sys.excepthook = self._handle_exception
        super().__init__()

        self.config = config
        
        # ensure the config and file handler are using the same timestamp
        # clean up output folder using the same logic for all file handlers 
        for name in logging.getHandlerNames():
            handler = logging.getHandlerByName(name)
            if isinstance(handler, CurrentTimeRotatingFileHandler):
                self.config.run_dt = handler.dt
                handler.rotator(join(dirname(self.config.output_folder), "{}"), self.config.output_folder)

        self.local: ConfigLocal = self.config.local[local]
        self.remote: ConfigRemote = self.config.remote[remote]
        self.api: ConfigAPI = self.remote.api

        self.local.library.remote_wrangler = self.remote.wrangler

        self.logger.debug(f"Initialisation of {self.__class__.__name__} object: DONE")

    def __call__(self, *args, **kwargs):
        main.logger.debug(f"Called processor '{self._processor_name}': START")
        super().__call__(*args, **kwargs)
        main.logger.debug(f"Called processor '{self._processor_name}': DONE\n")

    def set_processor(self, name: str) -> Callable:
        """Set the processor to use from the given name"""
        self._set_processor_name(name)
        return self._processor_method

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Custom exception handler. Handles exceptions through logger."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.critical(
            "CRITICAL ERROR: Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    def _save_json(self, filename: str, data: Mapping[str, Any], folder: str | None = None) -> None:
        """Save a JSON file to a given folder, or this run's folder if not given"""
        if not filename.casefold().endswith(".json"):
            filename += ".json"
        folder = folder or self.config.output_folder
        path = join(folder, filename)

        with open(path, "w") as file:
            json.dump(data, file, indent=2)

    def _load_json(self, filename: str, folder: str | None = None) -> dict[str, Any]:
        """Load a stored JSON file from a given folder, or this run's folder if not given"""
        if not filename.casefold().endswith(".json"):
            filename += ".json"
        folder = folder or self.config.output_folder
        path = join(folder, filename)

        with open(path, "r") as file:
            data = json.load(file)

        return data

    ###########################################################################
    ## Maintenance/Utilities
    ###########################################################################
    @dynamicprocessormethod
    def pause(self) -> None:
        """Pause the program with a message and wait for user input to continue"""
        input(f"\33[93m{self.config.pause_message}\33[0m ")
        self.logger.print()

    @dynamicprocessormethod
    def print(self) -> None:
        """Pretty print data from API getting input from user"""
        self.api.api.print_collection(use_cache=self.api.use_cache)

    @dynamicprocessormethod
    def reload(self) -> None:
        """Reload libraries"""
        self.logger.debug("Reload libraries: START")

        self.local.library.load(log=False)
        self.local.library_loaded = True

        self.remote.library.load(log=False)
        self.remote.library_loaded = True
        self.remote.library.extend(self.local.library, allow_duplicates=False)
        self.remote.library.enrich_tracks(artists=True)

        self.logger.debug("Reload libraries: DONE")

    ###########################################################################
    ## Backup/Restore
    ###########################################################################
    def local_backup_name(self, kind: str | None = None) -> str:
        """The identifier to use in filenames of the :py:class:`LocalLibrary`"""
        name = f"{self.local.library.__class__.__name__} - {self.local.library.name}"
        if kind:
            name = f"[{kind.upper()}] - {name}"
        return name

    def remote_backup_name(self, kind: str | None = None) -> str:
        """The identifier to use in filenames for backups of the :py:class:`RemoteLibrary`"""
        name = f"{self.remote.library.__class__.__name__} - {self.remote.library.name}"
        if kind:
            name = f"[{kind.upper()}] - {name}"
        return name

    @dynamicprocessormethod
    def backup(self, kind: str | None = None) -> None:
        """Backup data for all tracks and playlists in all libraries"""
        self.logger.debug("Backup libraries: START")
        self._save_json(self.local_backup_name(kind), self.local.library.json())
        self._save_json(self.remote_backup_name(kind), self.remote.library.json())
        self.logger.debug("Backup libraries: DONE")

    @dynamicprocessormethod
    def restore(self, kind: str | None = None) -> None:
        """Restore library data from a backup, getting user input for the settings"""
        output_parent = dirname(self.config.output_folder)
        backup_names = (self.local_backup_name(kind), self.remote_backup_name(kind))
        
        available_backups: list[str] = []  # names of the folders which contain usable backups
        for path in os.walk(output_parent):
            if path[0] == output_parent:  # skip current run's data
                continue
            folder = str(relpath(path[0], output_parent))
            
            for file in path[2]:
                if folder in available_backups:
                    break
                for name in backup_names:
                    if splitext(file)[0] == name:
                        available_backups.append(folder)
                        break
        
        if len(available_backups) == 0:
            self.logger.info("\33[93mNo backups found, skipping.\33[0m")
            return

        self.logger.info(
            "\33[97mAvailable backups: \n\t\33[97m- \33[94m{}\33[0m"
            .format("\33[0m\n\t\33[97m-\33[0m \33[94m".join(available_backups))
        )

        while True:  # get valid user input
            restore_from = get_user_input("Select the backup to use")
            if restore_from in available_backups:  # input is valid
                break
            print(f"\33[91mBackup '{restore_from}' not recognised, try again\33[0m")
        restore_from = join(output_parent, restore_from)

        restored = []
        if get_user_input(f"Restore {self.local_source} library tracks? (enter 'y')").casefold() == 'y':
            self._restore_local(restore_from, kind=kind)
            restored.append(self.local.library.name)
            self.logger.print()
        if get_user_input(f"Restore {self.remote_source} library playlists? (enter 'y')").casefold() == 'y':
            self._restore_spotify(restore_from, kind=kind)
            restored.append(self.remote_source)

        if not restored:
            self.logger.info(f"No libraries restored.")
            return
        self.logger.info(f"Successfully restored libraries: {", ".join(restored)}")

    def _restore_local(self, folder: str, kind: str | None = None) -> None:
        """Restore local library data from a backup, getting user input for the settings"""
        self.logger.debug("Restore local: START")
        self.logger.print()

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

        self.logger.print()
        if not self.local.library_loaded:
            self.local.library.load(tracks=True, playlists=False, log=False)

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Restoring local track tags from backup: "
            f"{basename(folder)} | Tags: {', '.join(restore_tags)}\33[0m"
        )
        backup = self._load_json(self.local_backup_name(kind), folder)

        # restore and save
        self.local.library.restore_tracks(backup["tracks"], tags=LocalTrackField.from_name(*restore_tags))
        results = self.local.library.save_tracks(tags=tags, replace=True, dry_run=self.config.dry_run)

        self.local.library.log_sync_result(results)
        self.logger.debug("Restore local: DONE")

    def _restore_spotify(self, folder: str, kind: str | None = None) -> None:
        """Restore remote library data from a backup, getting user input for the settings"""
        self.logger.debug(f"Restore {self.remote_source}: START")
        self.logger.print()

        if not self.remote.library_loaded:
            self.remote.library.load(log=False)
            self.remote.library_loaded = True

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Restoring {self.remote_source} playlists from backup: {basename(folder)} \33[0m"
        )
        backup = self._load_json(self.remote_backup_name(kind), folder)

        # restore and sync
        self.remote.library.restore_playlists(backup["playlists"])
        results = self.remote.library.sync(kind="refresh", reload=False, dry_run=self.config.dry_run)
        self.remote.library.log_sync(results)

        self.logger.debug(f"Restore {self.remote_source}: DONE")

    @dynamicprocessormethod
    def extract(self) -> None:
        """Extract and save images from local or remote items"""
        # TODO: add library-wide image extraction method
        raise NotImplementedError

    ###########################################################################
    ## Report/Search functions
    ###########################################################################
    @dynamicprocessormethod
    def report(self) -> None:
        """Produce various reports on loaded data"""
        self.logger.debug("Generate reports: START")
        for report in self.config.reports:
            if not report.enabled:
                continue

            if not self.local.library_loaded:
                self.local.library.load(log=False)
                self.local.library_loaded = True

            if isinstance(report, ConfigLibraryDifferences):
                if not self.remote.library_loaded:
                    self.remote.library.load(log=False)
                    self.remote.library_loaded = True

                source = self.config.filter.process(self.local.library.playlists.values())
                reference = self.config.filter.process(self.remote.library.playlists.values())
                report_playlist_differences(source=source, reference=reference)
            elif isinstance(report, ConfigMissingTags):
                source = self.config.filter.process(self.local.library.albums)
                report_missing_tags(collections=source, tags=report.tags, match_all=report.match_all)

        self.logger.debug("Generate reports: DONE")

    @dynamicprocessormethod
    def check(self) -> None:
        """Run check on entire library by album and update URI tags on file"""
        def finalise():
            """Finalise function operation"""
            self.logger.print()
            self.logger.debug("Check and update URIs: DONE")

        self.logger.debug("Check and update URIs: START")
        if not self.local.library_loaded:
            self.local.library.load(log=False)
            self.local.library_loaded = True

        folders = self.config.filter.process(self.local.library.folders)
        if not self.remote.checker(folders):
            finalise()
            return

        self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local.library)} tracks: uri \33[0m")
        results = self.local.library.save_tracks(tags=LocalTrackField.URI, replace=True, dry_run=self.config.dry_run)

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        self.logger.info(f"\33[92m    Done | Set tags for {len(results)} tracks \33[0m")

        finalise()

    @dynamicprocessormethod
    def search(self) -> None:
        """Run all methods for searching, checking, and saving URI associations for local files."""
        self.logger.debug("Search and match: START")

        albums = self.local.library.albums
        [album.items.remove(track) for album in albums for track in album.items.copy() if track.has_uri is not None]
        [albums.remove(album) for album in albums.copy() if len(album.items) == 0]

        if len(albums) == 0:
            self.logger.info("\33[1;95m ->\33[0;90m All items matched or unavailable. Skipping search.\33[0m")
            self.logger.print()
            return

        self.remote.searcher(albums)
        self.remote.checker(albums)

        self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local.library)} tracks: uri \33[0m")
        results = self.local.library.save_tracks(
            source=albums, tags=LocalTrackField.URI, replace=True, dry_run=self.config.dry_run
        )

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        log_prefix = "Would have set" if self.config.dry_run else "Set"
        self.logger.info(f"\33[92m    Done | {log_prefix} tags for {len(results)} tracks \33[0m")

        self.logger.print()
        self.logger.debug("Search and match: DONE")

    ###########################################################################
    ## Export from Syncify to sources
    ###########################################################################
    @dynamicprocessormethod
    def pull_tags(self) -> None:
        """Run all methods for pulling tag data from remote and updating local track tags"""
        self.logger.debug("Update tags: START")
        if not self.remote.library_loaded:
            self.remote.library.load(log=False)
            self.remote.library_loaded = True

        # add extra local tracks to remote library and merge remote items to local library
        self.remote.library.extend(self.local.library, allow_duplicates=False)
        self.remote.library.enrich_tracks(artists=True)
        self.local.library.merge_tracks(self.remote.library, tags=self.local.update.tags)

        # save tags to files
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local.library)} tracks: "
            f"{', '.join(t.name.lower() for t in self.local.update.tags)} \33[0m"
        )
        results = self.local.library.save_tracks(
            tags=self.local.update.tags, replace=self.local.update.replace, dry_run=self.config.dry_run
        )

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        log_prefix = "Would have set" if self.config.dry_run else "Set"
        self.logger.info(f"\33[92m    Done | {log_prefix} tags for {len(results)} tracks \33[0m")

        self.logger.print()
        self.logger.debug("Update tags: DONE")

    @dynamicprocessormethod
    def process_compilations(self) -> None:
        """Run all methods for setting and updating local track tags for compilation albums"""
        self.logger.debug("Update compilations: START")
        if not self.local.library_loaded:
            self.local.library.load(log=False)
            self.local.library_loaded = True

        folders = self.config.filter.process(self.local.library.folders)
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Setting and saving compilation style tags "
            f"for {sum(len(folder) for folder in folders)} tracks in {len(folders)} folders\n"
            f"\33[0;90m    Tags: {', '.join(t.name.lower() for t in self.local.update.tags)} \33[0m"
        )

        for folder in folders:
            folder.set_compilation_tags()
        results = self.local.library.save_tracks(
            source=folders, tags=self.local.update.tags, replace=self.local.update.replace, dry_run=self.config.dry_run
        )

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        log_prefix = "Would have set" if self.config.dry_run else "Set"
        self.logger.info(f"\33[92m    Done | {log_prefix} tags for {len(results)} tracks \33[0m")

        self.logger.print()
        self.logger.debug("Update compilations: Done\n")

    @dynamicprocessormethod
    def sync_spotify(self) -> None:
        """Run all main functions for synchronising remote playlists with a local library"""
        self.logger.debug(f"Update {self.remote_source}: START")
        if not self.local.library_loaded:
            self.local.library.load(tracks=False, log=False)

        playlists = self.local.library.get_filtered_playlists(
            include=self.remote.playlists.include,
            exclude=self.remote.playlists.exclude,
            **self.remote.playlists.filter
        )

        results = self.remote.library.sync(
            playlists,
            kind=self.remote.playlists.sync.kind,
            reload=self.remote.playlists.sync.reload,
            dry_run=self.config.dry_run
        )

        self.remote.library.log_sync(results)
        self.logger.debug(f"Update {self.remote_source}: DONE")


if __name__ == "__main__":
    print_logo()

    conf = Config()
    conf.load_log_config("logging.yml")
    conf.load("general")

    main = Syncify(config=conf, local="main", remote="spotify")
    functions = sys.argv[1:]

    if main.logger.file_paths:
        main.logger.info(f"\33[90mLogs: {", ".join(main.logger.file_paths)} \33[0m")
    main.logger.info(f"\33[90mOutput: {conf.output_folder} \33[0m")
    main.logger.print(logging.INFO)

    main.remote.api.api.authorise()
    for i, func in enumerate(functions, 1):
        conf.load(func, fail_on_missing=False)
        if conf.dry_run:
            print_line("DRY RUN ENABLED", " ")

        title = f"{PROGRAM_NAME}: {func}"
        if conf.dry_run:
            title += " (DRYRUN)"

        if sys.platform == "win32":
            os.system(f"title {title}")
        elif sys.platform == "linux" or sys.platform == "darwin":
            os.system(f"echo '\033]2;{title}\007'")

        if not conf.dry_run:
            exit()

        try:  # run the functions requested by the user
            method = main.set_processor(func)

            if method == main.backup and i == len(functions):
                print_line(f"final_{func}")
                main.backup("FINAL")
            else:
                print_line(func)
                main()
        except (Exception, KeyboardInterrupt):
            main.logger.critical(traceback.format_exc())
            break

    main.logger.debug(f"Time taken: {main.time_taken}")
    logging.shutdown()
    print_logo()
    print_time(main.time_taken)


## BIGGER ONES
# TODO: function to open search website tabs for all songs in 2get playlist
#  on common music stores/torrent sites
# TODO: Automatically add songs added to each remote playlist to '2get'?
#  Then somehow update local library playlists after...
#  Maybe add a final step that syncs remote back to library if
#  URIs for extra songs in remote playlists found in library
# TODO: track audio recognition when searching using Shazam like service?
#  Maybe https://audd.io/ ?
# TODO: expand search/match functionality to include all item types
# TODO: new music playlist that adds songs from artists user follows that
#  have been released within a given timeframe e.g. a day
# TODO: expand docstrings everywhere


## SMALLER/GENERAL ONES
# TODO: parallelize all the things
# TODO: generally improve performance
# TODO: look into the requests_cache, it grows way too big sometimes?
# TODO: implement terminal parser for function-specific kwargs?
# TODO: implement release structure on GitHub


## SELECTED FOR DEVELOPMENT
# TODO: test on linux/mac
#  - concerned about local playlist saving
#  - linux does not pick up 'include' paths when loading xautopf playlists
#    this is possibly due to case-sensitive paths not being found in linux
#    from using lowercase path cleaning logic in TrackMatch
#  This may now be fixed by extending functionality of playlists to include
#   available track paths on load
# TODO: implement merge_playlists functions and, by extension, implement android library sync
# TODO: implement XAutoPF full update functionality


## NEEDED FOR v0.3
# TODO: write tests, write tests, write tests
# TODO: update the readme (dynamic readme?)
# TODO: review scope of functions/attributes/properties
