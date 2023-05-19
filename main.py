import json
import os
import random

import pyfiglet
import re
import shutil
import traceback
from datetime import datetime as dt
from glob import glob
from os.path import basename, dirname, isdir, join, relpath
from time import perf_counter
from typing import List, Optional, Mapping, Any, Callable, MutableMapping

from dateutil.relativedelta import relativedelta

from syncify.local.library import LocalLibrary, MusicBee
from syncify.local.track.base.tags import TagName
from syncify.report import Report
from syncify.settings import Settings
from syncify.spotify.api import API
from syncify.spotify.library import SpotifyLibrary
from syncify.spotify.library.response import SpotifyResponse
from syncify.spotify.processor import Searcher, Checker
from syncify.spotify.processor.search import AlgorithmSettings
from syncify.utils.logger import Logger
from syncify.utils.helpers import get_user_input


class Syncify(Settings, Report):

    @property
    def allowed_functions(self) -> List[str]:
        return [method for method, value in Syncify.__dict__.items()
                if not method.startswith('_') and callable(value)
                and method not in ["set_func"]]

    @property
    def time_taken(self) -> float:
        return perf_counter() - self._start_time

    @property
    def api(self) -> API:
        if self._api is None:
            self._api = API(**self.cfg_run["spotify"]["api"]["settings"])
            SpotifyResponse.api = self._api
        return self._api

    @property
    def use_cache(self) -> bool:
        return self.cfg_run.get("spotify", {}).get("api", {}).get("use_cache", True)

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
    def local_library_backup_name(self):
        return f"{self.local_library.__class__.__name__} - {self.local_library.name}"

    @property
    def spotify_library(self) -> SpotifyLibrary:
        if self._spotify_library is None:
            use_cache = self.cfg_run["spotify"]["api"].get("use_cache", True)
            include = self.cfg_run["spotify"].get("playlists", {}).get("include")
            exclude = self.cfg_run["spotify"].get("playlists", {}).get("exclude")

            self._spotify_library = SpotifyLibrary(api=self.api, include=include, exclude=exclude, use_cache=use_cache)
        return self._spotify_library

    @property
    def spotify_library_backup_name(self):
        return f"{self.spotify_library.__class__.__name__} - {self.spotify_library.name}"

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
        """Set the current runtime function to call at ``self.run`` and set its config for this run"""
        self.run = getattr(self, name)
        self.cfg_run = self.cfg_functions.get(name, self.cfg_general)

    def save_json(self, filename: str, data: Mapping[str, Any], folder: Optional[str] = None):
        """Save a JSON file to a given folder, or this run's folder if not given"""
        if not filename.lower().endswith(".json"):
            filename += ".json"
        folder = folder if folder else self.output_folder
        path = join(folder, filename)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_json(self, filename: str, folder: Optional[str] = None) -> MutableMapping[str, Any]:
        """Load a stored JSON file from a given folder, or this run's folder if not given"""
        if not filename.lower().endswith(".json"):
            filename += ".json"
        folder = folder if folder else self.output_folder
        path = join(folder, filename)

        with open(path, "r") as f:
            data = json.load(f)

        return data

    ###########################################################################
    ## Maintenance/Utilities
    ###########################################################################
    def pause(self):
        """Pause the program with a message and wait for user input to continue"""
        message = self.cfg_run.get("message", "Pausing, hit return to continue...").strip()
        input(f"\33[93m{message}\33[0m ")

    def reload(self):
        """Reload libraries if they are initialised"""
        self.logger.debug("Reload libraries: START")

        if self._local_library is not None:
            self.local_library.load(tracks=True, playlists=True, log=False)
        if self._spotify_library is not None:
            self.spotify_library.use_cache = self.use_cache
            self.spotify_library.load(log=False)

        self.logger.debug("Reload libraries: DONE\n")

    def clean_syncify_files(self) -> None:
        """Clears files older than a number of days and only keeps max # of runs"""
        self.logger.debug("Clean Syncify files: START")

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

        self.logger.info(f"\33[1;95m ->\33[1;92m Removed {len(remove)} folders")
        self.logger.debug("Clean Syncify files: DONE\n")

    ###########################################################################
    ## Backup/Restore
    ###########################################################################
    def backup(self) -> None:
        """Backup data for all tracks and playlists in all libraries"""
        self.logger.debug("Backup libraries: START")
        self.save_json(self.local_library_backup_name, self.local_library.as_json())
        self.save_json(self.spotify_library_backup_name, self.spotify_library.as_json())
        self.logger.debug("Backup libraries: DONE\n")

    def restore(self) -> None:
        """Restore library data from a backup, getting user input for the settings"""
        output_parent = dirname(self.output_folder)
        available_backup_names = [relpath(i[0], output_parent) for i in os.walk(output_parent)
                                  if i[0] != output_parent
                                  and len([file for file in i[2] if file.lower().endswith(".json")]) > 0]
        if len(available_backup_names) == 0:
            self.logger.info("\33[93mNo backups found, skipping.\33[0m")

        self.logger.info("\33[97mAvailable backups: \n\t\33[97m- \33[94m{n}\33[0m"
                         .format(n='\33[0m\n\t\33[97m-\33[0m \33[94m'.join(available_backup_names)))
        while True:
            restore_from = get_user_input("Select tags to restore")
            if restore_from in available_backup_names:
                break
            print(f"\33[91mBackup '{restore_from}' not recognised, try again\33[0m")
        restore_from = join(output_parent, restore_from)

        if get_user_input("Restore local library tracks? (enter 'y')").lower() == 'y':
            self._restore_local(restore_from)
        if get_user_input("Restore Spotify library playlists? (enter 'y')").lower() == 'y':
            self._restore_spotify(restore_from)

    def _restore_local(self, folder: str):
        """Restore local library data from a backup, getting user input for the settings"""
        self.logger.debug("Restore local: START")

        tags = [tag.name.lower() for tag in TagName.all()]
        self.logger.info(f"\33[97mAvailable tags to restore: \33[94m{', '.join(tags)}\33[0m")
        message = "Select tags to restore separated by a space (entering nothing restores all available tags)"
        while True:
            restore_tags = [t.lower().strip() for t in get_user_input(message).split()]
            if not restore_tags:
                restore_tags = TagName.all()
                break
            if all(t in tags for t in restore_tags):
                restore_tags = [TagName.from_name(tag) for tag in restore_tags]
                break
            print(f"\33[91mTags entered were not recognised ({', '.join(restore_tags)}), try again\33[0m")

        tag_names = ', '.join(t for tag in restore_tags for t in tag.to_tag())
        self.logger.info(f"\33[1;95m ->\33[1;97m Restoring local track tags from backup: "
                         f"{basename(folder)} | Tags: {tag_names}\33[0m")
        self.print_line()
        backup = self.load_json(self.local_library_backup_name, folder)

        self.local_library.restore_tracks(backup["tracks"], tags=restore_tags)
        self.local_library.save_tracks(tags=tags, replace=True, dry_run=self.dry_run)

        self.logger.debug("Restore local: DONE\n")

    def _restore_spotify(self, folder: str):
        """Restore Spotify library data from a backup, getting user input for the settings"""
        self.logger.debug("Restore Spotify: START")

        self.logger.info(f"\33[1;95m ->\33[1;97m Restoring Spotify playlists from backup: {basename(folder)} \33[0m")
        self.print_line()
        backup = self.load_json(self.spotify_library_backup_name, folder)

        self.spotify_library.restore_playlists(backup["playlists"])
        self.spotify_library.sync(clear='all', reload=False)

        self.logger.debug("Restore Spotify: DONE\n")

    def extract(self):
        """Extract and save images from local or Spotify items"""
        raise NotImplementedError

    ###########################################################################
    ## Report/Search functions
    ###########################################################################
    def report(self) -> None:
        """Produce various reports on loaded data"""
        self.logger.debug("Generate reports: START")
        self.report_library_differences(self.local_library, self.spotify_library)
        self.report_missing_tags(self.local_library.folders)
        self.logger.debug("Generate reports: DONE\n")

    def check(self) -> None:
        """Run check on entire library by album and update URI tags on file"""
        self.logger.debug("Check and update URIs: START")

        albums = self.local_library.albums
        cfg = self.cfg_run["spotify"]
        SpotifyResponse.api = self.api

        allow_karaoke = AlgorithmSettings.ITEMS.allow_karaoke
        checker = Checker(api=self.api, allow_karaoke=allow_karaoke)
        checker.check(albums, interval=cfg.get("check", {}).get("interval", 10))

        self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local_library)} tracks: uri \33[0m")
        results = self.local_library.save_tracks(tags=TagName.URI, replace=True, dry_run=self.dry_run)

        saved = sum(r.saved for r in results.values())
        updated = sum(len(r.updated) > 0 for r in results.values())
        self.logger.info(f"\33[92m    Done | Set tags for {updated} tracks | Saved {saved} tracks \33[0m")

        self.logger.debug("Check and update URIs: DONE\n")

    def search(self) -> None:
        """
        Run all methods for searching, checking, and storing URI associations for local files.
        This does not save URI associations to the file.
        """
        self.logger.debug("Search and match: START")

        albums = self.local_library.albums
        [album.items.remove(track) for album in albums for track in album.items.copy() if track.has_uri is not None]
        [albums.remove(album) for album in albums.copy() if len(album.items) == 0]

        if len(albums) == 0:
            self.logger.info("\33[1;95m ->\33[0;90m All items matched or unavailable. Skipping search.\33[0m")
            return

        cfg = self.cfg_run["spotify"]
        SpotifyResponse.api = self.api

        allow_karaoke = AlgorithmSettings.ITEMS.allow_karaoke
        searcher = Searcher(api=self.api, allow_karaoke=allow_karaoke)
        searcher.search(albums)

        checker = Checker(api=self.api, allow_karaoke=allow_karaoke)
        checker.check(albums, interval=cfg.get("check", {}).get("interval", 10))

        self.logger.debug("Search and match: DONE\n")

    ###########################################################################
    ## Export from Syncify to sources
    ###########################################################################
    def get_tags(self) -> None:
        """Run all methods for synchronising local data with Spotify and updating local track tags"""
        self.logger.debug("Update tags: START")

        replace = self.cfg_run.get("local", {}).get("update", {}).get("replace", False)
        tag_names = self.cfg_run.get("local", {}).get("update", {}).get("tags")
        tags = TagName.ALL if not tag_names else[TagName.from_name(tag_name) for tag_name in tag_names]

        # add extra local tracks to Spotify library and merge Spotify items to local library
        self.spotify_library.extend(self.local_library)
        self.local_library.merge_items(self.spotify_library, tags=tags)

        self.logger.info(f"\33[1;95m ->\33[1;97m Updating tags for {len(self.local_library)} tracks: "
                         f"{', '.join(t.name.lower() for t in tags)} \33[0m")
        results = self.local_library.save_tracks(tags=tags, replace=replace, dry_run=self.dry_run)

        saved = sum(r.saved for r in results.values())
        updated = sum(len(r.updated) > 0 for r in results.values())
        self.logger.info(f"\33[92m    Done | Set tags for {updated} tracks | Saved {saved} tracks \33[0m")
        self.logger.debug("Update tags: DONE\n")

    def process_compilations(self):
        """Run all methods for setting and updating local track tags for compilation albums"""
        self.logger.debug("Update compilations: START")

        include_prefix = self.cfg_run.get("filter", {}).get("include", {}).get("prefix", "").strip().lower()
        exclude_prefix = self.cfg_run.get("filter", {}).get("exclude", {}).get("prefix", "").strip().lower()
        start = self.cfg_run.get("filter", {}).get("start", "").strip().lower()
        stop = self.cfg_run.get("filter", {}).get("stop", "").strip().lower()

        folders = []
        for folder in self.local_library.folders:
            name = folder.name.strip().lower()
            conditionals = [not include_prefix or name.startswith(include_prefix),
                            not exclude_prefix or not name.startswith(exclude_prefix),
                            not start or name >= start, not stop or name <= stop]
            if all(conditionals):
                folders.append(folder)

        replace = self.cfg_run.get("local", {}).get("update", {}).get("replace", False)
        tag_names = self.cfg_run.get("local", {}).get("update", {}).get("tags")
        tags = TagName.ALL if not tag_names else[TagName.from_name(tag_name) for tag_name in tag_names]
        item_count = sum(len(folder) for folder in folders)

        self.logger.info(f"\33[1;95m ->\33[1;97m Setting and saving compilation style tags "
                         f"for {item_count} tracks in {len(folders)} folders: "
                         f"{', '.join(t.name.lower() for t in tags)} \33[0m")

        results = {}
        for folder in folders:
            folder.set_compilation_tags()
            results.update(folder.save_tracks(tags=tags, replace=replace, dry_run=self.dry_run))

        saved = sum(r.saved for r in results.values())
        updated = sum(len(r.updated) > 0 for r in results.values())
        self.logger.info(f"\33[92m    Done | Set tags for {updated} tracks | Saved {saved} tracks \33[0m")
        self.logger.debug("Update compilations: Done\n")

    def sync_spotify(self) -> None:
        """Run all main functions for synchronising Spotify playlists with a local library"""
        self.logger.debug("Update Spotify: START")

        if self._local_library is not None:  # reload local library
            self.local_library.load(tracks=False, playlists=True, log=False)

        cfg_playlists = self.cfg_run.get("spotify", {}).get("playlists", {})

        filter_tags = cfg_playlists.get("sync", {}).get("filter", {})
        include = cfg_playlists.get("include")
        exclude = cfg_playlists.get("exclude")
        playlists = self.local_library.get_filtered_playlists(include=include, exclude=exclude, **filter_tags)

        clear = cfg_playlists.get("sync", {}).get("clear")
        reload = cfg_playlists.get("sync", {}).get("reload")
        self.spotify_library.sync(playlists, clear=clear, reload=reload)

        self.logger.debug("Update Spotify: DONE\n")


# noinspection SpellCheckingInspection
def print_logo():
    fonts = ["basic", "broadway", "chunky", "doom", "drpepper", "epic", "hollywood", "isometric2",
             "larry3d", "shadow", "slant", "speed", "standard", "univers", "whimsy"]
    colours = [91, 93, 92, 94, 96, 95]
    if bool(random.getrandbits(1)):
        colours.reverse()

    cols = os.get_terminal_size().columns
    figlet = pyfiglet.Figlet(font=random.choice(fonts), direction=0, justify="left", width=cols)

    text = figlet.renderText("SYNCIFY").rstrip().split("\n")
    text_width = max(len(line) for line in text)
    indent = int((cols - text_width) / 2)

    for i, line in enumerate(text):
        print(f"{' ' * indent}\33[1;{colours[i % len(colours)]}m{line}\33[0m")
    print()


def print_line(text: str = ""):
    text = text.replace("_", " ").title()
    cols = os.get_terminal_size().columns

    amount_left = (cols - (len(text) + 2)) // 2
    output_len = amount_left * 2 + len(text) + 2
    amount_right = amount_left + (1 if output_len < cols else 0)
    print(f"\n\33[1;96m{'-' * amount_left} \33[95m{text}\33[1;96m {'-' * amount_right}\33[0m\n")


def print_time(seconds: float):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    text = f"{mins} mins {secs} secs"

    cols = os.get_terminal_size().columns
    indent = int((cols - len(text)) / 2)

    print(f"\33[1;95m{' ' * indent}{text}\33[0m")


if __name__ == "__main__":
    main = Syncify()
    # env.get_kwargs()
    main.parse_from_prompt()
    print_logo()
    main.logger.info(f"\33[90mLogs: {main.log_path} \33[0m")
    main.logger.info(f"\33[90mOutput: {main.output_folder} \33[0m")

    for func in main.functions:
        try:  # run the functions requested by the user
            main.set_func(func)
            main.logger.debug(f"START function: {func}")
            print_line(func)
            main.run()
            # main._close_handlers()
            main.logger.debug(f"DONE  function: {func}")
        except BaseException:
            main.logger.critical(traceback.format_exc())
            break

    print_logo()
    print_time(main.time_taken)

# TODO: track audio recognition when searching using Shazam like service?
# TODO: Automatically add songs added to each Spotify playlist to '2get'?
#  Then somehow update local library playlists after...
#  Maybe add a final step that syncs Spotify back to library if
#  uris for extra songs in Spotify playlists found in library
# TODO: function to open search website tabs for all songs in 2get playlist
#  on common music stores/torrent sites
# TODO: genres are still not being populated from Spotify
# TODO: increment position number on successive tqdm bars when getting
#  reset when position=0 finishes
