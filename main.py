import argparse
import json
import logging
import os
import re
import sys
import traceback
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from os.path import basename, dirname, join, relpath, splitext
from time import perf_counter
from typing import Any, Callable

from syncify import PROGRAM_NAME
from syncify.config import Config, ConfigLibraryDifferences, ConfigMissingTags, ConfigRemote, ConfigLocal
from syncify.exception import ConfigError
from syncify.fields import LocalTrackField
from syncify.local.collection import LocalCollection
from syncify.local.track import LocalTrack, SyncResultTrack
from syncify.processors.base import DynamicProcessor, dynamicprocessormethod
from syncify.remote.api import RemoteAPI
from syncify.remote.enums import RemoteObjectType
from syncify.remote.object import RemoteAlbum
from syncify.report import report_playlist_differences, report_missing_tags
from syncify.utils.helpers import get_user_input, UnitIterable, to_collection
from syncify.utils.logger import SyncifyLogger, STAT, CurrentTimeRotatingFileHandler, REPORT
from syncify.utils.printers import print_logo, print_line, print_time


class Syncify(DynamicProcessor):
    """Core functionality and meta-functions for the program"""

    @property
    def time_taken(self) -> float:
        """The total time taken since initialisation"""
        return perf_counter() - self._start_time

    @property
    def local(self) -> ConfigLocal:
        """The local config for this session"""
        config = self.config.libraries[self.local_name]
        if not isinstance(config, ConfigLocal):
            raise ConfigError("The given name does not relate to the config for a local library")
        return config

    @property
    def remote(self) -> ConfigRemote:
        """The remote config for this session"""
        config = self.config.libraries[self.remote_name]
        if not isinstance(config, ConfigRemote):
            raise ConfigError("The given name does not relate to the config for a remote library")
        return config

    @property
    def api(self) -> RemoteAPI:
        """The API currently being used for the remote source"""
        return self.remote.api.api

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
                self.config.dt = handler.dt
                handler.rotator(join(dirname(self.config.output_folder), "{}"), self.config.output_folder)

        self.local_name: str = local
        self.remote_name: str = remote
        self.local.remote_wrangler = self.remote.wrangler

        self.logger.debug(f"Initialisation of {self.__class__.__name__} object: DONE")

    def __call__(self, *args, **kwargs):
        main.logger.debug(f"Called processor '{self._processor_name}': START")
        if self.local_name in self.config.reload:
            self.reload_local(*self.config.reload[self.local_name])
        if self.remote_name in self.config.reload:
            self.reload_remote(*self.config.reload[self.remote_name])

        super().__call__(*args, **kwargs)

        if self.config.pause:
            input(f"\33[93m{self.config.pause}\33[0m ")
            main.logger.print()

        main.logger.debug(f"Called processor '{self._processor_name}': DONE\n")

    def set_processor(self, name: str) -> Callable:
        """Set the processor to use from the given name"""
        self._set_processor_name(name)
        self.config.load(func)
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
    ## Utilities
    ###########################################################################
    @dynamicprocessormethod
    def print(self, *_, **__) -> None:
        """Pretty print data from API getting input from user"""
        self.api.print_collection(use_cache=self.remote.api.use_cache)

    def reload_local(self, *kinds: str) -> None:
        """Fully reload local library"""
        self.logger.debug("Reload local library: START")

        load_all = not kinds
        self.local.library.load(tracks=load_all or "tracks" in kinds, playlists=load_all or "playlists" in kinds)

        self.local.library_loaded = True
        self.logger.debug("Reload local library: DONE")

    def reload_remote(self, *kinds: str) -> None:
        """Fully reload remote library"""
        self.logger.debug("Reload remote library: START")

        load_all = not kinds
        if load_all:
            self.remote.library.load()
        else:
            if "playlists" in kinds:
                self.remote.library.load_playlists()
            if "saved_tracks" in kinds:
                self.remote.library.load_saved_tracks()
            if "saved_albums" in kinds:
                self.remote.library.load_saved_albums()
            if "saved_artists" in kinds:
                self.remote.library.load_saved_artists()

            self.logger.print(REPORT)
            self.remote.library.log_playlists()
            self.remote.library.log_tracks()
            self.remote.library.log_albums()
            self.remote.library.log_artists()
            self.logger.print()

        if load_all or "extend" in kinds:
            self.remote.library.extend(self.local.library, allow_duplicates=False)
        if load_all or "enrich" in kinds:
            if load_all or "tracks" in kinds or "saved_tracks" in kinds:
                self.remote.library.enrich_tracks(
                    artists=load_all or "artists" in kinds, albums=load_all or "albums" in kinds
                )
            if load_all or "saved_albums" in kinds:
                self.remote.library.enrich_saved_albums()
            if load_all or "saved_artists" in kinds:
                self.remote.library.enrich_saved_artists(tracks=load_all or "tracks" in kinds)

        self.remote.library_loaded = True
        self.logger.debug("Reload remote library: DONE")

    def save_tracks(
            self,
            collections: UnitIterable[LocalCollection[LocalTrack]] | None = None,
            tags: UnitIterable[LocalTrackField] = LocalTrackField.ALL,
            replace: bool = False
    ) -> dict[LocalTrack, SyncResultTrack]:
        """
        Saves the tags of all tracks in the given ``collections``.

        :param collections: The collections containing the tracks which you wish to save.
        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :return: A map of the :py:class:`LocalTrack` saved to its result as a :py:class:`SyncResultTrack` object
        """
        tracks: tuple[LocalTrack, ...] = tuple(track for coll in to_collection(collections) for track in coll)
        bar = self.logger.get_progress_bar(iterable=tracks, desc="Updating tracks", unit="tracks")
        results = {track: track.save(tags=tags, replace=replace, dry_run=self.config.dry_run) for track in bar}
        return {track: result for track, result in results.items() if result.updated}

    ###########################################################################
    ## Backup/Restore
    ###########################################################################
    def local_backup_name(self, key: str | None = None) -> str:
        """The identifier to use in filenames of the :py:class:`LocalLibrary`"""
        name = f"{self.local.library.__class__.__name__} - {self.local.library.name}"
        if key:
            name = f"[{key.upper()}] - {name}"
        return name

    def remote_backup_name(self, key: str | None = None) -> str:
        """The identifier to use in filenames for backups of the :py:class:`RemoteLibrary`"""
        name = f"{self.remote.library.__class__.__name__} - {self.remote.library.name}"
        if key:
            name = f"[{key.upper()}] - {name}"
        return name

    @dynamicprocessormethod
    def backup(self, key: str | None = None, *_, **__) -> None:
        """Backup data for all tracks and playlists in all libraries"""
        self.logger.debug("Backup libraries: START")
        if not key:
            key = get_user_input("Enter a key for this backup. Hit return to backup without a key")

        if not self.local.library_loaded:
            self.reload_local()
        if not self.remote.library_loaded:
            self.reload_remote("tracks", "playlists")

        self._save_json(self.local_backup_name(key), self.local.library.json())
        self._save_json(self.remote_backup_name(key), self.remote.library.json())
        self.logger.debug("Backup libraries: DONE")

    @dynamicprocessormethod
    def restore(self, *_, **__) -> None:
        """Restore library data from a backup, getting user input for the settings"""
        output_parent = dirname(self.config.output_folder)
        backup_names = (self.local_backup_name(), self.remote_backup_name())
        
        available_backups: list[str] = []  # names of the folders which contain usable backups
        for path in os.walk(output_parent):
            if path[0] == output_parent:  # skip current run's data
                continue
            folder = str(relpath(path[0], output_parent))
            
            for file in path[2]:
                if folder in available_backups:
                    break
                for name in backup_names:
                    if name in splitext(file)[0]:
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
        available_keys = [re.sub(r"^\[(\w+)].*", "\\1", file).casefold() for file in os.listdir(restore_from)]

        self.logger.info(
            "\33[97mAvailable backup keys: \n\t\33[97m- \33[94m{}\33[0m"
            .format("\33[0m\n\t\33[97m-\33[0m \33[94m".join(available_keys))
        )

        while True:  # get valid user input
            key = get_user_input("Select the backup type to use")
            if key.casefold() in available_keys:  # input is valid
                break
            print(f"\33[91mBackup '{key}' not recognised, try again\33[0m")

        restored = []
        if get_user_input(f"Restore {self.local.source} library tracks? (enter 'y')").casefold() == 'y':
            self._restore_local(restore_from, key=key)
            restored.append(self.local.library.name)
            self.logger.print()
        if get_user_input(f"Restore {self.remote.source} library playlists? (enter 'y')").casefold() == 'y':
            self._restore_spotify(restore_from, key=key)
            restored.append(self.remote.source)

        if not restored:
            self.logger.info(f"No libraries restored.")
            return
        self.logger.info(f"Successfully restored libraries: {", ".join(restored)}")

    def _restore_local(self, folder: str, key: str | None = None) -> None:
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
        if not self.local.library_loaded:  # not a full load so don't mark the library as loaded
            self.reload_local("tracks")

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Restoring local track tags from backup: "
            f"{basename(folder)} | Tags: {', '.join(restore_tags)}\33[0m"
        )
        backup = self._load_json(self.local_backup_name(key), folder)

        # restore and save
        self.local.library.restore_tracks(backup["tracks"], tags=LocalTrackField.from_name(*restore_tags))
        results = self.local.library.save_tracks(tags=tags, replace=True, dry_run=self.config.dry_run)

        self.local.library.log_sync_result(results)
        self.logger.debug("Restore local: DONE")

    def _restore_spotify(self, folder: str, key: str | None = None) -> None:
        """Restore remote library data from a backup, getting user input for the settings"""
        self.logger.debug(f"Restore {self.remote.source}: START")
        self.logger.print()

        if not self.remote.library_loaded:
            self.reload_remote("tracks", "playlists")

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Restoring {self.remote.source} playlists from backup: {basename(folder)} \33[0m"
        )
        backup = self._load_json(self.remote_backup_name(key), folder)

        # restore and sync
        self.remote.library.restore_playlists(backup["playlists"])
        results = self.remote.library.sync(kind="refresh", reload=False, dry_run=self.config.dry_run)
        self.remote.library.log_sync(results)

        self.logger.debug(f"Restore {self.remote.source}: DONE")

    @dynamicprocessormethod
    def extract(self, *_, **__) -> None:
        """Extract and save images from local or remote items"""
        # TODO: add library-wide image extraction method
        raise NotImplementedError

    ###########################################################################
    ## Report/Search functions
    ###########################################################################
    @dynamicprocessormethod
    def report(self, *_, **__) -> None:
        """Produce various reports on loaded data"""
        self.logger.debug("Generate reports: START")
        for report in self.config.reports:
            if not report.enabled:
                continue

            if not self.local.library_loaded:
                self.reload_local()

            if isinstance(report, ConfigLibraryDifferences) and self.local.library.playlists:
                if not self.remote.library_loaded:
                    self.reload_remote("playlists")
                if not self.remote.library.playlists:
                    continue

                source = report.filter.process(self.local.library.playlists.values())
                reference = self.config.filter.process(self.remote.library.playlists.values())
                report_playlist_differences(source=source, reference=reference)
            elif isinstance(report, ConfigMissingTags):
                source = report.filter.process(self.local.library.albums)
                report_missing_tags(collections=source, tags=report.tags, match_all=report.match_all)

        self.logger.debug("Generate reports: DONE")

    @dynamicprocessormethod
    def check(self, *_, **__) -> None:
        """Run check on entire library by album and update URI tags on file"""
        def finalise():
            """Finalise function operation"""
            self.logger.print()
            self.logger.debug("Check and update URIs: DONE")

        self.logger.debug("Check and update URIs: START")
        if not self.local.library_loaded:
            self.reload_local()

        folders = self.config.filter.process(self.local.library.folders)
        if not self.remote.checker(folders):
            finalise()
            return

        self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local.library)} tracks: uri \33[0m")
        results = self.local.library.save_tracks(tags=LocalTrackField.URI, replace=True, dry_run=self.config.dry_run)

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        self.logger.info(f"\33[92mSet tags for {len(results)} tracks \33[0m")

        finalise()

    @dynamicprocessormethod
    def search(self, *_, **__) -> None:
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
        results = self.save_tracks(collections=albums, tags=LocalTrackField.URI, replace=True)

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        log_prefix = "Would have set" if self.config.dry_run else "Set"
        self.logger.info(f"\33[92m{log_prefix} tags for {len(results)} tracks \33[0m")

        self.logger.print()
        self.logger.debug("Search and match: DONE")

    ###########################################################################
    ## Miscellaneous library operations
    ###########################################################################
    @dynamicprocessormethod
    def pull_tags(self, *_, **__) -> None:
        """Run all methods for pulling tag data from remote and updating local track tags"""
        self.logger.debug("Update tags: START")
        # if not self.local.library_loaded:
        #     self.reload_remote("tracks")
        # if not self.remote.library_loaded:
        #     self.reload_remote("tracks", "playlists", "extend", "artists")

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
        self.logger.info(f"\33[92m{log_prefix} tags for {len(results)} tracks \33[0m")

        self.logger.print()
        self.logger.debug("Update tags: DONE")

    @dynamicprocessormethod
    def process_compilations(self, *_, **__) -> None:
        """Run all methods for setting and updating local track tags for compilation albums"""
        self.logger.debug("Update compilations: START")
        if not self.local.library_loaded:
            self.reload_local("tracks")

        folders = self.config.filter.process(self.local.library.folders)
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Setting and saving compilation style tags "
            f"for {sum(len(folder) for folder in folders)} tracks in {len(folders)} folders\n"
            f"\33[0;90m    Tags: {', '.join(t.name.lower() for t in self.local.update.tags)} \33[0m"
        )

        for folder in folders:
            folder.set_compilation_tags()
        results = self.save_tracks(collections=folders, tags=self.local.update.tags, replace=self.local.update.replace)

        if results:
            self.logger.print(STAT)
        self.local.library.log_sync_result(results)
        log_prefix = "Would have set" if self.config.dry_run else "Set"
        self.logger.info(f"\33[92m{log_prefix} tags for {len(results)} tracks \33[0m")

        self.logger.print()
        self.logger.debug("Update compilations: Done\n")

    @dynamicprocessormethod
    def sync_remote(self, *_, **__) -> None:
        """Run all main functions for synchronising remote playlists with a local library"""
        self.logger.debug(f"Sync {self.remote.source}: START")
        if not self.local.library_loaded:  # not a full load so don't mark the library as loaded
            self.reload_local("playlists")

        playlists = self.local.library.get_filtered_playlists(
            include=self.remote.playlists.include,
            exclude=self.remote.playlists.exclude,
            **self.remote.playlists.sync.filter
        )

        results = self.remote.library.sync(
            playlists,
            kind=self.remote.playlists.sync.kind,
            reload=self.remote.playlists.sync.reload,
            dry_run=self.config.dry_run
        )

        self.remote.library.log_sync(results)
        self.logger.debug(f"Sync {self.remote.source}: DONE")

    @dynamicprocessormethod
    def new_music(self, name: str, start: date | datetime, end: date | datetime = datetime.now(), *_, **__):
        """Create a new music playlist for followed artists with music released between ``start`` and ``end``"""
        self.logger.debug(f"New music playlist: START")

        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()

        self.logger.info(
            f"\33[1;95m ->\33[1;97m Creating '{name}' {self.remote.source} playlist "
            f"for new tracks by followed artists released between {start} and {end} \33[0m"
        )

        # load saved artists and their albums with fresh data, ignoring use_cache settings
        if not self.remote.library_loaded or not all(artist.albums for artist in self.remote.library.artists):
            use_cache_original = self.remote.library.use_cache
            self.remote.library.use_cache = False
            self.remote.library.load_saved_artists()
            self.remote.library.use_cache = use_cache_original

            self.remote.library.enrich_saved_artists(types=("album", "single"))

        def match_date(alb: RemoteAlbum) -> bool:
            """Match start and end dates to the release date of this given ``album``"""
            return any({
                alb.date and start <= alb.date <= end,
                alb.month and start.year <= alb.year <= end.year and start.month <= alb.month <= end.month,
                alb.year and start.year <= alb.year <= end.year,
            })

        # filter albums and check if any albums need extending
        albums = [album for artist in self.remote.library.artists for album in artist.albums if match_date(album)]
        albums_need_extend = [album for album in albums if len(album.tracks) < album.track_total]
        if albums_need_extend:
            kind = RemoteObjectType.ALBUM
            key = self.api.collection_item_map[kind]

            bar = self.logger.get_progress_bar(iterable=albums_need_extend, desc="Getting album tracks", unit="albums")
            for album in bar:
                self.api.extend_items(album.response, kind=kind, key=key, use_cache=self.remote.api.use_cache)
                album.refresh(skip_checks=False)

        # log load results
        if not self.remote.library_loaded or albums_need_extend:
            self.logger.print(REPORT)
            self.remote.library.log_artists()
            self.logger.print()

        tracks = [track for album in sorted(albums, key=lambda x: x.date, reverse=True) for track in album]
        self.logger.info(f"\33[1;95m  >\33[1;97m Adding {len(tracks)} tracks to '{name}' \33[0m")

        pl = self.remote.library.playlists.get(name)
        if pl is None:  # playlist not loaded, attempt to find playlist on remote with fresh data
            responses = self.remote.api.api.get_user_items(use_cache=False)
            for response in responses:
                pl_check = self.remote.playlist(response=response, api=self.remote.api.api, skip_checks=True)

                if pl_check.name == name:
                    self.remote.api.api.get_items(response, kind=RemoteObjectType.PLAYLIST, use_cache=False)
                    pl_check.refresh(skip_checks=False)
                    pl = pl_check
                    break

        if pl is None:  # if playlist still not found, create it
            pl = self.remote.playlist.create(api=self.remote.api.api, name=name)

        # add tracks to remote playlist
        pl.extend(tracks, allow_duplicates=False)
        results = pl.sync(kind="refresh", reload=False, dry_run=False)

        self.logger.print(STAT)
        self.remote.library.log_sync({name: results})
        self.logger.info(f"\33[92mAdded {results.added} new tracks to playlist: '{name}' \33[0m")
        self.logger.debug(f"New music playlist: DONE")


# noinspection PyProtectedMember
def get_parser() -> argparse.ArgumentParser:
    """Get the terminal input parser"""
    parser = argparse.ArgumentParser(
        description="Sync your local library to remote libraries and other useful functions.",
        prog=PROGRAM_NAME,
        usage="%(prog)s [options] [function]"
    )
    parser._positionals.title = "Functions"
    parser._optionals.title = "Optional arguments"

    # cli function aliases and expected args in order user should give them
    parser.add_argument(
        "functions", nargs="*", choices=list(Syncify.__new__(Syncify).__processormethods__),
        help=f"{PROGRAM_NAME} function to run."
    )

    runtime = parser.add_argument_group("Runtime options")
    runtime.add_argument(
        "-c", "--config", type=str, required=False, nargs="?", dest="config_path",
        default="config.yml",
        help="The path to the config file to use"
    )
    runtime.add_argument(
        "-k", "--config-key", type=str, required=False, nargs="?", dest="config_key",
        default="general",
        help="The key for the initial config."
    )
    runtime.add_argument(
        "-lc", "--log-config", type=str, required=False, nargs="?", dest="log_config_path",
        default="logging.yml",
        help="The path to the logging config file to use"
    )
    runtime.add_argument(
        "-ln", "--log-name", type=str, required=False, nargs="?", dest="log_name",
        help="The logger settings to use for this run as can be found in logging config file"
    )
    runtime.add_argument(
        "-x", "--execute", action="store_false", dest="dry_run",
        help="Modify user's local and remote files and playlists. Otherwise, do not affect files."
    )

    libraries = parser.add_argument_group("Library options")
    libraries.add_argument(
        "-l", "--local", type=str, required=True, nargs="?", dest="local",
        help="The name of the local library to use as can be found in the config file"
    )
    libraries.add_argument(
        "-r", "--remote", type=str, required=True, nargs="?", dest="remote",
        help="The name of the remote library to use as can be found in the config file"
    )

    functions = parser.add_argument_group("Function options")
    functions.add_argument(
        "-bk", "--backup-key", type=str, required=False, nargs="?", dest="backup_key",
        default=None,
        help="When running backup operations, the key to give to backups"
    )
    functions.add_argument(
        "-nmn", "--new-music-name", type=str, required=False, nargs="?", dest="new_music_name",
        default="New Music",
        help="When running new_music operations, the name to give to the new music playlist"
    )
    functions.add_argument(
        "-nms", "--new-music-start", required=False, nargs="?", dest="new_music_start",
        type=lambda x: datetime.strptime(x, "%Y-%m-%d"), default=datetime.now() - timedelta(weeks=4),
        help="When running new_music operations, the earliest date to get new music for"
    )
    functions.add_argument(
        "-nme", "--new-music-end", required=False, nargs="?", dest="new_music_end",
        type=lambda x: datetime.strptime(x, "%Y-%m-%d"), default=datetime.now(),
        help="When running new_music operations, the latest date to get new music for"
    )

    return parser


if __name__ == "__main__":
    print()
    print_logo()
    named_args = get_parser().parse_known_args()[0]

    conf = Config(named_args.config_path)
    conf.load_log_config(named_args.log_config_path, named_args.log_name, __name__)
    conf.load(named_args.config_key)
    conf.dry_run = named_args.dry_run

    main = Syncify(config=conf, local=named_args.local, remote=named_args.remote)

    # log header
    if main.logger.file_paths:
        main.logger.info(f"\33[90mLogs: {", ".join(main.logger.file_paths)} \33[0m")
    main.logger.info(f"\33[90mOutput: {conf.output_folder} \33[0m")
    main.logger.print()
    if conf.dry_run:
        print_line("DRY RUN ENABLED", " ")

    main.api.authorise()
    for i, func in enumerate(named_args.functions, 1):
        title = f"{PROGRAM_NAME}: {func}"
        if conf.dry_run:
            title += " (DRYRUN)"

        if sys.platform == "win32":
            os.system(f"title {title}")
        elif sys.platform == "linux" or sys.platform == "darwin":
            os.system(f"echo '\033]2;{title}\007'")

        try:  # run the functions requested by the user
            print_line(func)
            # initialise the libraries
            assert main.local.library is not None
            assert main.remote.library is not None

            method = main.set_processor(func)
            main(
                key=named_args.backup_key,
                name=named_args.new_music_name,
                start=named_args.new_music_start,
                end=named_args.new_music_end,
            )
        except (Exception, KeyboardInterrupt):
            main.logger.critical(traceback.format_exc())
            break

    main.logger.debug(f"Time taken: {main.time_taken}")
    logging.shutdown()
    print_logo()
    print_time(main.time_taken)


## BIGGER ONES
# TODO: Automatically add songs added to each remote playlist to '2get'?
#  Then somehow update local library playlists after...
#  Maybe add a final step that syncs remote back to library if
#  URIs for extra songs in remote playlists found in library
# TODO: track audio recognition when searching using Shazam like service?
#  Maybe https://audd.io/ ?
# TODO: add lyrics property to tracks? Possibly through a separate API
# TODO: expand search/match functionality to include all item types
# TODO: expand docstrings everywhere


## SMALLER/GENERAL ONES
# TODO: parallelize all the things
# TODO: generally improve performance
# TODO: revisit the config logic, it's a bit of a mess


## SELECTED FOR DEVELOPMENT
# TODO: expand readme + check all python functions work
# TODO: implement XAutoPF full update functionality
# TODO: implement merge_playlists functions and, by extension, implement android library sync
# TODO: release to pypi + implement CI/CD structure on GitHub
# TODO: function to open search website tabs for all songs in 2get playlist
#  on common music stores/torrent sites
