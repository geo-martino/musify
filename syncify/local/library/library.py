from glob import glob
from glob import glob
from os.path import splitext, join, exists, basename
from typing import Optional, List, Set, MutableMapping, Mapping, Collection, Any, Union

from syncify.abstract import Item
from syncify.abstract.collection import Library, ItemCollection
from syncify.abstract.misc import Result
from syncify.local.file import IllegalFileTypeError
from syncify.local.library.collection import LocalCollection, LocalFolder, LocalAlbum, LocalArtist, LocalGenres
from syncify.local.playlist import __PLAYLIST_FILETYPES__, LocalPlaylist, M3U, XAutoPF
from syncify.local.playlist.processor import TrackSort
from syncify.local.track import __TRACK_CLASSES__, LocalTrack, load_track
from syncify.local.track.base.tags import PropertyName, TagName
from syncify.utils.logger import Logger


class LocalLibrary(Library, LocalCollection):
    """
    Represents a local library, providing various methods for manipulating
    tracks and playlists across an entire local library collection.

    :param library_folder: The absolute path of the library folder containing all tracks.
        The intialiser will check for the existence of this path and only store it if it exists.
    :param playlist_folder: The absolute path of the playlist folder containing all playlists
        or the relative path within the given ``library_folder``.
        The intialiser will check for the existence of this path and only store the absolute path if it exists.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param include: An optional list of playlist names to include when loading playlists.
    :param exclude: An optional list of playlist names to exclude when loading playlists.
    :param load: When True, load the library on intialisation.
    """

    @property
    def library_folder(self) -> str:
        return self._library_folder

    @library_folder.setter
    def library_folder(self, value: Optional[str]):
        if value is None:
            return
        self._library_folder: str = value.rstrip("\\/")
        self._track_paths = None
        if value is not None:
            self._track_paths = {path for c in __TRACK_CLASSES__ for path in c.get_filepaths(self._library_folder)}

    @property
    def playlist_folder(self) -> str:
        return self._playlist_folder

    @playlist_folder.setter
    def playlist_folder(self, value: Optional[str]):
        if value is None:
            return
        if not exists(value) and self.library_folder is not None:
            value = join(self.library_folder.rstrip("\\/"), value.lstrip("\\/"))
        if not exists(value):
            return

        self._playlist_folder: str = value.rstrip("\\/")
        self._playlist_paths = None
        if value is not None:
            playlists = {}
            for filetype in __PLAYLIST_FILETYPES__:
                paths = glob(join(self._playlist_folder, "**", f"*{filetype}"), recursive=True)
                entry = {splitext(basename(path.replace(self._playlist_folder, "").lower()))[0]: path for path in paths}
                playlists.update(entry)

            playlists_total = len(playlists)
            self._playlist_paths = {name: path for name, path in sorted(playlists.items(), key=lambda x: x[0])
                                    if (not self.include or name in self.include)
                                    and (not self.exclude or name not in self.exclude)}

            self.logger.debug(f"Filtered out {playlists_total - len(self._playlist_paths)} playlists "
                              f"from {playlists_total} Spotify playlists")

    @property
    def name(self) -> Optional[str]:
        return basename(self.library_folder) if self.library_folder else None

    @property
    def playlists(self) -> MutableMapping[str, LocalPlaylist]:
        return self._playlists

    @property
    def folders(self) -> List[LocalFolder]:
        grouped = TrackSort.group_by_field(tracks=self.tracks, field=PropertyName.FOLDER)
        collections = [LocalFolder(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    @property
    def albums(self) -> List[LocalAlbum]:
        grouped = TrackSort.group_by_field(tracks=self.tracks, field=TagName.ALBUM)
        collections = [LocalAlbum(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    @property
    def artists(self) -> List[LocalArtist]:
        grouped = TrackSort.group_by_field(tracks=self.tracks, field=TagName.ARTIST)
        collections = [LocalArtist(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    @property
    def genres(self) -> List[LocalGenres]:
        grouped = TrackSort.group_by_field(tracks=self.tracks, field=TagName.GENRES)
        collections = [LocalGenres(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    def __init__(
            self,
            library_folder: Optional[str] = None,
            playlist_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None,
            include: Optional[List[str]] = None,
            exclude: Optional[List[str]] = None,
            load: bool = True,
    ):
        Logger.__init__(self)

        self.include = [name.strip().lower() for name in include] if include else None
        self.exclude = [name.strip().lower() for name in exclude] if exclude else None

        self._library_folder: Optional[str] = None
        # name of track object to set of paths valid for that track object
        self._track_paths: Optional[Set[str]] = None
        self.library_folder = library_folder

        self._playlist_folder: Optional[str] = None
        # playlist lowercase name mapped to its filepath for all accepted filetypes in playlist folder
        self._playlist_paths: Optional[MutableMapping[str, str]] = None
        self.playlist_folder = playlist_folder

        self.other_folders = other_folders

        self.tracks: List[LocalTrack] = []
        self._playlists: MutableMapping[str, LocalPlaylist] = {}

        if load:
            self.logger.info(f"\33[1;95m ->\33[1;97m Loading local library of "
                             f"{len(self._track_paths)} tracks and {len(self._playlist_paths)} playlists \33[0m")
            self.print_line()
            self.load()

    def load(self) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self.logger.debug("Load local library: START")

        self.tracks = self.load_tracks()
        self.print_line()
        self.log_tracks()
        print()

        self._playlists = {pl.name: pl for pl in sorted(self.load_playlists(), key=lambda pl: pl.name.casefold())}
        self.print_line()
        self.log_playlists()
        print()

        self.logger.debug("Load local library: DONE\n")

    def load_tracks(self) -> List[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        return self._load_tracks()

    def _load_tracks(self) -> List[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        self.logger.debug("Load local tracks: START")
        self.logger.info(f"\33[1;95m  >\33[1;97m "
                         f"Extracting metadata and properties for {len(self._track_paths)} tracks \33[0m")

        tracks: List[LocalTrack] = []
        errors: List[str] = []
        for path in self.get_progress_bar(iterable=self._track_paths, desc="Loading tracks", unit="tracks"):
            try:
                tracks.append(load_track(path=path))
            except Exception:
                errors.append(path)
                continue

        self._log_errors(errors)
        self.logger.debug("Load local tracks: DONE\n")
        return tracks

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        self.logger.info(
            f"\33[1;96m{'LIBRARY TOTALS':<22}\33[1;0m|"
            f"\33[92m{sum([track.has_uri is not None for track in self.tracks]):>6} available \33[0m|"
            f"\33[91m{sum([track.has_uri is None for track in self.tracks]):>6} missing \33[0m|"
            f"\33[93m{sum([track.has_uri is False for track in self.tracks]):>6} unavailable \33[0m|"
            f"\33[1m{len(self.tracks):>6} total \33[0m"
        )

    def load_playlists(self, names: Optional[Collection[str]] = None) -> List[LocalPlaylist]:
        """
        Load a playlist from a given list of names or, if None, load all playlists in this library.
        The name must be relative to the playlist folder of this object and exist in its loaded paths.

        :param names: Playlist paths to load relative to the playlist folder.
        :return: The loaded playlists.
        :exception KeyError: If a given playlist name cannot be found.
        """
        self.logger.debug("Load local playlist data: START")
        if names is None:
            names = self._playlist_paths.keys()

        self.logger.info(f"\33[1;95m  >\33[1;97m Loading playlist data for {len(names)} playlists \33[0m")

        playlists: List[LocalPlaylist] = []
        errors: List[str] = []
        for name in self.get_progress_bar(iterable=names, desc="Loading playlists", unit="playlists"):
            path = self._playlist_paths.get(name.strip().lower())
            if path is None:
                raise KeyError(f"Playlist name not found in the stored paths of this manager: {name}")

            ext = splitext(path)[1].lower()
            if ext in M3U.valid_extensions:
                pl = M3U(
                    path=path, tracks=self.tracks, library_folder=self.library_folder, other_folders=self.other_folders
                )
            elif ext in XAutoPF.valid_extensions:
                pl = XAutoPF(
                    path=path, tracks=self.tracks, library_folder=self.library_folder, other_folders=self.other_folders
                )
            else:
                raise IllegalFileTypeError(ext)

            playlists.append(pl)

        self._log_errors(errors)
        self.logger.debug("Load local playlist data: DONE\n")
        return playlists

    def save_playlists(self, dry_run: bool = True) -> Mapping[str, Result]:
        """Saves the tags of all tracks in this library. Use arguments from :py:func:`LocalPlaylist.save()`"""
        return {name: pl.save(dry_run=dry_run) for name, pl in self.playlists.items()}

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = self.get_max_width(self.playlists)

        self.logger.info("\33[1;96mFound the following Local playlists: \33[0m")
        for name, playlist in self.playlists.items():
            self.logger.info(
                f"{self.truncate_align_str(name, max_width=max_width)} |"
                f"\33[92m{len([t for t in playlist if t.has_uri]):>4} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t.has_uri is None]):>4} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t.has_uri is False]):>4} unavailable \33[0m|"
                f"\33[1m {len(playlist):>4} total \33[0m"
            )

    def _log_errors(self, errors: List[str]) -> None:
        """Log paths which had some error while loading"""
        if len(errors) > 0:
            self.logger.debug("Could not load: \33[91m\n\t- {errors} \33[0m".format(errors="\n\t- ".join(errors)))

    def restore_uris(self, backup: str, remove: bool = True) -> None:
        """
        Restore URIs from a backup to loaded track objects. This does not save the updated tags.

        :param backup: Filename of backup json in form <path>: <uri>.
        :param remove: If True, when a lookup to the back for a URI returns None, remove the URI from the track.
            If False, keep the current value in the track.
        """
        # TODO: complete and test me
        self.logger.info(f"\33[1;95m -> \33[1;97mRestoring URIs from backup file: {backup} \33[0m")

        backup: Mapping[str, str] = {path.lower(): uri for path, uri in self.load_json(backup).items()}
        count = 0
        for track in self.tracks:
            uri = backup.get(track.path.lower())
            if remove or uri is not None:
                track.uri = uri
                count += 1

        self.logger.info(f"\33[92mRestored URIs for {count} tracks \33[0m")

    def extend(self, items: Union[ItemCollection, Collection[Item]]) -> None:
        self.tracks.extend(track for track in items if isinstance(track, LocalTrack) and track not in self.tracks)

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "library_folder": self.library_folder,
            "playlists_folder": self.playlist_folder,
            "other_folders": self.other_folders,
            "track_count": len(self.tracks),
            "playlist_counts": {name: len(pl) for name, pl in self._playlists.items()},
        }
