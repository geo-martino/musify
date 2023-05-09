import os
import re
from glob import glob
from os.path import (basename, dirname, exists, join, normpath, sep,
                     splitext)

from syncify.local.musicbee import MusicBee


class Playlists(MusicBee):

    def __init__(self):
        MusicBee.__init__(self)

    def restore_local_playlists(self, backup: str, in_playlists: list=None, ex_playlists: list=None, dry_run: bool = True, **kwargs):
        """
        Restore local playlists from backup.

        :param backup: str. Filename of backup json in form <name>: <list of dicts of track's metadata>
        :param in_playlists: list, default=None. Only restore playlists in this list.
        :param ex_playlists: list, default=None. Don't restore playlists in this list.
        :param dry_run: bool, default=True. Don't save if True, save if False.
        """

        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mRestoring local playlists from backup file: {backup} \33[0m")

        backup = self.load_json(backup, parent=True, **kwargs)
        if not backup:
            self._logger.info(f"\33[91mBackup file not found.\33[0m")
            return

        if isinstance(in_playlists, str):  # handle string
            in_playlists = [in_playlists]

        if in_playlists is not None:
            for name, tracks in backup.copy().items():
                if name.lower() not in [p.lower() for p in in_playlists]:
                    del backup[name]
        else:
            in_playlists = list(backup.keys())

        if ex_playlists is not None:
            for name in backup.copy().keys():
                if name.lower() in [p.lower() for p in ex_playlists]:
                    del backup[name]

        if not dry_run:
            for name, tracks in backup.items():
                name = re.sub(r'[\\/*?:"<>|]', '', name)
                self.save_m3u([t['path'] for t in tracks], name, **kwargs)

            self._logger.info(f"\33[92mRestored {len(backup)} local playlists \33[0m")

    def _filter_paths(self, paths: list, name: str):
        start_count = len(paths)
        if start_count == 0:  # playlist is empty
            return paths

        # get filtered list of paths to add back
        missing = set(paths) - set(self._all_files)
        changed_count = 0
        for i, path in enumerate(paths):
            if path in missing:
                found = False
                for actual_path in self._all_files:
                    if path.lower() == actual_path.lower():
                        paths[i] = actual_path
                        found = True
                        changed_count += 1
                        break
                
                if not found:
                    paths[i] = None
        
        paths = [path for path in paths if path is not None]
        if start_count - len(paths) > 0 or changed_count > 0:
            self._logger.debug(
                f"{name} | "
                f"{start_count - len(paths)} paths removed | "
                f"{changed_count} path cases changed")
        else:
            self._logger.debug(f"{name} | No paths changed")
        return paths

    def clean_playlists(self, **kwargs):
        """
        Remove dead links and fix case of links in all xautopf and m3u playlists
        """
        # get playlist paths
        playlists = glob(join(self._playlists_path, '**', '*.xautopf'), recursive=True)
        playlists += glob(join(self._playlists_path, '**', '*.m3u'), recursive=True)

        print()
        self._logger.info(
            f'\33[1;95m -> \33[1;97mCleaning paths in {len(playlists)} Local playlists\33[0m')
        
        names = [splitext(basename(path))[0] for path in playlists]
        max_width = len(max(names, key=len)) + 1 if len(max(names, key=len)) + 1 < 50 else 50

        for playlist_path in playlists:
            name = basename(playlist_path)
            name_log = f"{name if len(name) < 50 else name[:47] + '...':<{max_width}}"

            if playlist_path.endswith('.xautopf'):  # load xml like object
                raw_xml = self.load_autoplaylist(playlist_path)
                source = raw_xml['SmartPlaylist']['Source']

                include = source.get('ExceptionsInclude')
                include = include.split('|') if isinstance(include, str) else []
                include_filtered = self._filter_paths(include, f"{name_log} In")
                if len(include_filtered) > 0:
                    source['ExceptionsInclude'] = '|'.join(include_filtered)
                elif source.get('ExceptionsInclude'):
                    source['ExceptionsInclude']

                exclude = source.get('Exceptions')
                exclude = exclude.split('|') if isinstance(exclude, str) else []
                exclude_filtered = self._filter_paths(exclude, f"{name_log} Ex")
                if len(exclude_filtered) > 0:
                    source['Exceptions'] = '|'.join(exclude_filtered)
                elif source.get('Exceptions'):
                    del source['Exceptions']

                self.save_autoplaylist(raw_xml, name, **kwargs)
            elif playlist_path.endswith('.m3u'):  # load list of paths
                paths = self.load_m3u(playlist_path)
                paths_filtered = self._filter_paths(paths, f"{name_log}   ")
                self.save_m3u(paths_filtered, name, **kwargs)

    ###########################################################################
    ## Compare for synchronisation
    ###########################################################################
    def _get_stem_path_map(self):
        return {self._clean_path(path, self._music_path): path for path in self._all_files}

    def _clean_path(self, path: str, remove_prefix: str="", stems: list=None):
        remove_prefix = normpath(remove_prefix).replace("\\", "\\\\")
        remove_prefix = remove_prefix.replace(".", "\.")
        path = re.sub(f"^{remove_prefix}", "", normpath(path)).lstrip(sep)
        for ext in self._tag_ids:
            path = re.sub(f"{ext.replace('.', '')}$", "", normpath(path))
        
        if stems and path not in stems:
            for stem in stems:
                if path.lower() == stem.lower():
                    return stem
            raise FileNotFoundError(f"Stem not found: {path}")
        
        return path
    
    def _clean_paths(self, tracks: list, remove_prefix: str="", stems: list=None):
        if len(tracks) == 0:
            return tracks
        elif isinstance(tracks[0], dict):
            tracks = [track['path'] for track in tracks]
        return [self._clean_path(path, remove_prefix, stems) for path in tracks if len(path) > 1]

    def _load_playlists(self, playlists_path: str, remove_prefix: str="", stems: list=None):
        if not exists(dirname(playlists_path)):
            os.makedirs(dirname(playlists_path))
        m3u_paths = glob(join(playlists_path, '**', '*.m3u'), recursive=True)
        playlists = {}
        path_sep = '/'
        for playlist_path in m3u_paths:
            name = splitext(basename(playlist_path))[0]
            tracks = self.load_m3u(playlist_path)
            if len(tracks) == 0:
                continue
            path_sep = '\\' if '\\' in tracks[0] else '/'
            playlists[name] = self._clean_paths(tracks, remove_prefix, stems)
        
        return playlists, path_sep
            

    def _get_changes(self, current: dict, previous: dict, blacklist: dict=None):
        changes = {}
        blacklist = {} if blacklist is None else blacklist
        
        for name, tracks in current.items():
            changes[name] = {"added": [], "removed": []}
            if name not in previous:
                changes[name]["added"] = tracks
                continue
            
            blacklist_pl = blacklist.get(name, {"added": [], "removed": []})
            for path in tracks:  # added tracks
                if not path in previous[name] and not path in blacklist_pl["removed"]:
                    changes[name]["added"].append(path)
            for path in previous[name]:  # removed tracks
                if not path in tracks and not path in blacklist_pl["added"]:
                    changes[name]["removed"].append(path)
        
        return changes

    def _update_autoplaylist(self, path: str, current: list, added: list, removed: list, max_width: int = 0, **kwargs):
        name = splitext(basename(path))[0]
        name_log = f"{name if len(name) < 50 else name[:47] + '...':<{max_width}}"
        logger = self._logger.info if self._verbose > 0 else self._logger.debug

        xml = self.load_autoplaylist(path, **kwargs)
        source = xml["SmartPlaylist"]["Source"]
        include = source.get("ExceptionsInclude")
        exclude = source.get("Exceptions")
        
        include = include.split("|") if isinstance(include, str) else []
        exclude = exclude.split("|") if isinstance(exclude, str) else []

        include_initial = include.copy()
        include = [path for path in include if path not in removed]
        include += [path for path in added if path not in include and path not in exclude]
        include_added = list(set(include) - set(include_initial))
        include_removed = list(set(include_initial) - set(include))

        if len(include_added) + len(include_removed) > 0:
            log_str = (
                f"\33[93m{len(include_added):>4} added \33[0m|"
                f"\33[91m{len(include_removed):>4} removed \33[0m|"
                f"\33[92;1m {len(include):>4} final \33[0m")
        else:    
            log_str = "\33[1m No changes\33[0m"
        logger(f"{name_log} | xautopf - include |"
            f"\33[96m{len(include_initial):>4} initial \33[0m|{log_str}")

        exclude_initial = exclude.copy()
        exclude = [path for path in exclude if path not in added]
        exclude += [path for path in removed if path in current and path not in include_removed]
        exclude_added = list(set(exclude) - set(exclude_initial))
        exclude_removed = list(set(exclude_initial) - set(exclude))
        
        if len(exclude_added) + len(exclude_removed) > 0:
            log_str = (
                f"\33[93m{len(exclude_added):>4} added \33[0m|"
                f"\33[91m{len(exclude_removed):>4} removed \33[0m|"
                f"\33[92;1m {len(exclude):>4} final \33[0m")
        else:    
            log_str = "\33[1m No changes\33[0m"
        logger(f"{name_log} | xautopf - exclude |"
            f"\33[96m{len(exclude_initial):>4} initial \33[0m|{log_str}")

        if len(include) > 0 or "ExceptionsInclude" in source:
            source["ExceptionsInclude"] = "|".join(include)
        if len(exclude) > 0 or "Exceptions" in source:
            source["Exceptions"] = "|".join(exclude)
        
        return xml
        

    def compare_playlists(self, playlists: dict, ext_playlists_path: str, export_alias: str, ext_path_prefix: str = "..", dry_run: bool=False, **kwargs):        
        print()
        self._logger.info(
            f'\33[1;95m -> \33[1;97mSynchronising Local and {export_alias} playlists\33[0m')

        stem_path_map = self._get_stem_path_map()

        local_current = {}
        for name, tracks in playlists.items():
            local_current[name] = self._clean_paths(tracks, self._music_path)
        
        export_path = join(dirname(self._data_path), export_alias)

        previous, _ = self._load_playlists(export_path, stems=stem_path_map)
        ext_current, ext_sep = self._load_playlists(ext_playlists_path, ext_path_prefix, stem_path_map)
        drop_playlists = [name for name in previous if name not in local_current]
        if exists(ext_playlists_path):
            drop_playlists += [name for name in previous if name not in ext_current]

        local_changes = self._get_changes(local_current, previous)
        ext_changes = self._get_changes(ext_current, previous, local_changes)
        

        synced_playlists = {}
        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        names = (set(ext_changes) | set(local_changes) | set(playlists)) - set(drop_playlists)
        max_width = len(max(names, key=len)) + 1 if len(max(names, key=len)) + 1 < 50 else 50

        if self._verbose > 0:
            print()

        for name in sorted(names, key=str.casefold):
            name_log = f"{name if len(name) < 50 else name[:47] + '...':<{max_width}}"
            tracks = local_current.get(name, [])
            tracks_initial = previous.get(name, [])
            tracks_added = []
            tracks_removed = []
            
            for changes in [ext_changes, local_changes]:
                if name in changes:
                    added = changes[name]["added"]
                    removed = changes[name]["removed"]

                    tracks_removed += [path for path in removed if path in tracks_initial]
                    tracks = [path for path in tracks if path not in removed]
                    tracks_added += [path for path in added if path not in tracks_initial]
                    tracks += [path for path in added if path not in tracks]
            
            synced_playlists[name] = tracks
            if len(set(tracks_added)) + len(set(tracks_removed)) > 0:
                log_str = (
                    f"\33[93m{len(set(tracks_added)):>4} added \33[0m|"
                    f"\33[91m{len(set(tracks_removed)):>4} removed \33[0m|"
                    f"\33[92;1m {len(synced_playlists[name]):>4} final \33[0m")
            else:    
                log_str = "\33[1m No changes\33[0m"
            logger(f"{name_log} | \33[96m{len(tracks_initial):>4} initial \33[0m|{log_str}")

        # export playlists to sub-folders in export path
        export = {}
        local_auto = glob(join(self._playlists_path, '**', '*.xautopf'), recursive=True)
        local_auto = {splitext(basename(path))[0]: path for path in local_auto}
        local_m3u = glob(join(self._playlists_path, '**', '*.m3u'), recursive=True)
        local_m3u = {splitext(basename(path))[0]: path for path in local_m3u}

        if self._verbose > 0:
            print()

        for name, tracks in synced_playlists.items():
            if name not in playlists and (name in local_m3u or name in local_auto):
                name_log = f"{name if len(name) < 50 else name[:47] + '...':<{max_width}}"
                logger(f"{name_log} | Removing playlist from external")
                continue
            ext_tracks = [ext_sep.join([ext_path_prefix] + path.split("\\")) for path in tracks]
            ext_tracks = [path[:-1] + '.mp3' for path in ext_tracks]
            export[join(ext_playlists_path, name)] = ext_tracks

            if name in local_m3u:
                export[local_m3u[name]] = [stem_path_map[stem] for stem in tracks]
            elif name in local_auto and name in ext_changes:
                current = [track['path'] for track in playlists[name]]
                added = [stem_path_map[stem] for stem in ext_changes[name]["added"]]
                removed = [stem_path_map[stem] for stem in ext_changes[name]["removed"]]
                xml = self._update_autoplaylist(local_auto[name], current, added, removed, max_width)
                export[local_auto[name]] = xml
            elif name not in local_auto:
                export[join(self._playlists_path, name)] = [stem_path_map[stem] for stem in tracks]

            export[join(export_path, name)] = tracks
            
        if not dry_run:
            [os.remove(path) for path in glob(join(ext_playlists_path, '*.m3u'))]
            [os.remove(path) for path in glob(join(export_path, '*.m3u'))]
        for path, data in export.items():
            if path.endswith(".xautopf"):
                self.save_autoplaylist(data, path, append_path=False, dry_run=dry_run, **kwargs)
            else:
                self.save_m3u(data, path, append_path=False, dry_run=dry_run, **kwargs)

        if self._verbose > 0:
            print()
        logger(f"\33[92mDone | Synchronised {len(synced_playlists)} playlists \33[0m")





