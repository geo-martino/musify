from datetime import datetime
from glob import glob
from os.path import splitext, join, exists
from typing import Optional, List, Set, MutableMapping, Mapping, Collection, Any, Callable, Tuple

from syncify.local.files import IllegalFileTypeError
from syncify.local.files.playlist import __PLAYLIST_FILETYPES__, LocalPlaylist, M3U, XAutoPF
from syncify.local.files.track import LocalTrackCollection, __TRACK_CLASSES__, LocalTrack, load_track, SyncResultTrack
from syncify.utils_new.generic import SyncResult
from utils.logger import Logger


class LocalLibrary(LocalTrackCollection, Logger):
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
    :param load: When True, load the library on intialisation.
    """

    @property
    def library_folder(self) -> str:
        return self._library_folder

    @library_folder.getter
    def library_folder(self) -> str:
        return self._library_folder

    @library_folder.setter
    def library_folder(self, value: Optional[str]):
        self._library_folder: str = value.rstrip("\\/") if value is not None and exists(value) else None
        self._track_paths = None
        if value is not None:
            self._track_paths = {c.__name__: c.get_filepaths(self._library_folder) for c in __TRACK_CLASSES__}

    @property
    def playlist_folder(self) -> str:
        return self._playlist_folder

    @playlist_folder.getter
    def playlist_folder(self) -> str:
        return self._playlist_folder

    @playlist_folder.setter
    def playlist_folder(self, value: Optional[str]):
        if not exists(value) and self.library_folder is not None:
            value = join(self.library_folder.rstrip("\\/"), value.lstrip("\\/"))
        if not exists(value):
            return

        self._playlist_folder: str = value.rstrip("\\/") if value is not None else None
        self._playlist_paths = None
        if value is not None:
            playlists = {}
            for filetype in __PLAYLIST_FILETYPES__:
                paths = glob(join(self._playlist_folder, "**", f"*{filetype}"), recursive=True)
                entry = {path.replace(self._playlist_folder, "").strip().lower(): path for path in paths}
                playlists.update(entry)
            self._playlist_paths = dict(sorted(playlists.items(), key=lambda x: x[0]))

    @property
    def tracks(self) -> List[LocalTrack]:
        return self._tracks

    @tracks.getter
    def tracks(self) -> List[LocalTrack]:
        return self._tracks

    @property
    def playlists(self) -> List[LocalPlaylist]:
        return self._playlists

    @playlists.getter
    def playlists(self) -> List[LocalPlaylist]:
        return self._playlists

    def __init__(
            self,
            library_folder: Optional[str] = None,
            playlist_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None,
            load: bool = True,
    ):
        Logger.__init__(self)

        self._library_folder: Optional[str] = None
        # name of track object to set of paths valid for that track object
        self._track_paths: Optional[Mapping[str, Set[str]]] = None
        self.library_folder = library_folder

        self._playlist_folder: Optional[str] = None
        # playlist lowercase name mapped to its filepath for all accepted filetypes in playlist folder
        self._playlist_paths: Optional[MutableMapping[str, str]] = None
        self.playlist_folder = playlist_folder

        self.other_folders = other_folders

        self._tracks: List[LocalTrack] = []
        self._playlists: List[LocalPlaylist] = []
        self.last_played: Optional[datetime] = None
        self.last_added: Optional[datetime] = None
        self.last_modified: Optional[datetime] = None

        if load:
            self.load()

    def load(self) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self._tracks = self.load_tracks()
        if len(self._tracks) > 0:
            key_type = Callable[[LocalTrack], Tuple[bool, datetime]]
            key: key_type = lambda t: (t.last_played is None, t.last_played)
            self.last_played = sorted(self._tracks, key=key, reverse=True)[0].last_played
            key: key_type = lambda t: (t.date_added is None, t.date_added)
            self.last_added = sorted(self._tracks, key=key, reverse=True)[0].date_added
            key: key_type = lambda t: (t.date_modified is None, t.date_modified)
            self.last_modified = sorted(self._tracks, key=key, reverse=True)[0].date_modified
        self.log_tracks()

        self._playlists = self.load_playlists()
        self.log_playlists()

    def load_tracks(self) -> List[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        return self._load_tracks()

    def _load_tracks(self) -> List[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        paths = [path for paths in self._track_paths.values() for path in paths]

        self._logger.info(f"\33[1;95m -> \33[1;97mExtracting metadata and properties for {len(paths)} tracks \33[0m")

        tracks: List[LocalTrack] = []
        errors: List[str] = []
        for path in self._get_progress_bar(iterable=paths, desc="Loading tracks", unit="tracks"):
            try:
                tracks.append(load_track(path=path))
            except Exception:
                errors.append(path)
                continue

        self._log_errors(errors)
        self._logger.debug("Loading track metadata: Done")
        return tracks

    def save_tracks(self, **kwargs) -> Mapping[str, SyncResultTrack]:
        """Saves the tags of all tracks in this library. Use arguments from :py:func:`LocalTrack.save()`"""
        return {track.path: track.save(**kwargs) for track in self.tracks}

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        if self._verbose > 0:
            print()
        self._logger.debug(
            f"\33[1;96mLIBRARY TOTALS       \33[1;0m|"
            f"\33[92m{sum([track.has_uri for track in self._tracks]):>6} available \33[0m|"
            f"\33[91m{sum([track.has_uri is None for track in self._tracks]):>6} missing \33[0m|"
            f"\33[93m{sum([track.has_uri is False for track in self._tracks]):>6} unavailable \33[0m|"
            f"\33[1m{len(self._tracks):>6} total \33[0m"
        )

    def load_playlists(self, names: Optional[Collection[str]] = None) -> List[LocalPlaylist]:
        """
        Load a playlist from a given list of names or, if None, load all playlists in this library.
        The name must be relative to the playlist folder of this object and exist in its loaded paths.

        :param names: Playlist paths to load relative to the playlist folder.
        :return: The loaded playlists.
        :exception KeyError: If a given playlist name cannot be found.
        """
        if names is None:
            names = self._playlist_paths.keys()

        self._logger.info(f"\33[1;95m -> \33[1;97mLoading playlist data for {len(names)} playlists \33[0m")

        playlists: List[LocalPlaylist] = []
        errors: List[str] = []
        for name in self._get_progress_bar(iterable=names, desc="Loading playlists", unit="playlists"):
            path = self._playlist_paths.get(name.strip().lower())
            if path is None:
                raise KeyError(f"Playlist name not found in the stored paths of this manager: {name}")

            ext = splitext(path)[1].lower()
            if ext in M3U.valid_extensions:
                pl = M3U(
                    path=path, tracks=self._tracks, library_folder=self.library_folder, other_folders=self.other_folders
                )
            elif ext in XAutoPF.valid_extensions:
                pl = XAutoPF(
                    path=path, tracks=self._tracks, library_folder=self.library_folder, other_folders=self.other_folders
                )
            else:
                raise IllegalFileTypeError(ext)

            playlists.append(pl)

        self._log_errors(errors)
        self._logger.debug("Loading playlist data: Done")
        return playlists

    def save_playlists(self, **kwargs) -> Mapping[str, SyncResult]:
        """Saves the tags of all tracks in this library. Use arguments from :py:func:`LocalTrack.save()`"""
        return {pl.name: pl.save(**kwargs) for pl in self.playlists}

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        playlists: Mapping[str, LocalPlaylist] = dict(sorted([(pl.name, pl) for pl in self._playlists], key=lambda x: x[0]))
        max_width = self._get_max_width(playlists)

        if self._verbose > 0:
            print()
        self._logger.debug("\33[1;96mFound the following Local playlists: \33[0m")
        for name, playlist in sorted(playlists.items(), key=lambda x: x[0].lower()):
            self._logger.debug(
                f"{self._truncate_align_str(name, max_width=max_width)} |"
                f"\33[92m{len([t for t in playlist if t.has_uri]):>4} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t.has_uri is None]):>4} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t.has_uri is False]):>4} unavailable \33[0m|"
                f"\33[1m {len(playlist):>4} total \33[0m"
            )

    def _log_errors(self, errors: List[str]) -> None:
        """Log paths which had some error while loading"""
        if len(errors) > 0:
            self._logger.debug("Could not load: \33[91m\n\t- {errors} \33[0m".format(errors="\n\t- ".join(errors)))

    def restore_uris(self, backup: str, remove: bool = True) -> None:
        """
        Restore URIs from a backup to loaded track objects. This does not save the updated tags.

        :param backup: Filename of backup json in form <path>: <uri>.
        :param remove: If True, when a lookup to the back for a URI returns None, remove the URI from the track.
            If False, keep the current value in the track.
        """
        self._logger.info(f"\33[1;95m -> \33[1;97mRestoring URIs from backup file: {backup} \33[0m")

        backup: Mapping[str, str] = {path.lower(): uri for path, uri in self.load_json(backup).items()}
        count = 0
        for track in self.tracks:
            uri = backup.get(track.path.lower())
            if remove or uri is not None:
                track.uri = uri
                count += 1

        self._logger.info(f"\33[92mRestored URIs for {count} tracks \33[0m")

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "library_folder": self.library_folder,
            "playlists_folder": self.playlist_folder,
            "other_folders": self.other_folders,
            "track_count": len(self._tracks),
            "playlist_counts": {pl.name: len(pl) for pl in self._playlists},
        }
