from collections.abc import Collection, Mapping, Iterable
from glob import glob
from os.path import splitext, join, exists, basename
from typing import Any

from syncify.abstract.collection import Playlist, Library
from syncify.abstract.item import Item
from syncify.abstract.misc import Result
from syncify.enums.tags import PropertyName, TagName
from syncify.local.exception import IllegalFileTypeError, LocalCollectionError
from syncify.local.playlist import __PLAYLIST_FILETYPES__, LocalPlaylist, M3U, XAutoPF
from syncify.local.playlist.processor.sort import TrackSorter
from syncify.local.track import __TRACK_CLASSES__, LocalTrack, load_track
from syncify.utils import UnitCollection, UnitIterable
from syncify.utils.logger import Logger, REPORT
from .collection import LocalCollectionFiltered, LocalFolder, LocalAlbum, LocalArtist, LocalGenres


class LocalLibrary(LocalCollectionFiltered[LocalTrack], Library[LocalTrack]):
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
    def tracks(self) -> list[LocalTrack]:
        """The tracks in this collection"""
        return self._tracks

    @property
    def library_folder(self) -> str:
        """Path to the library folder"""
        return self._library_folder

    @library_folder.setter
    def library_folder(self, value: str | None):
        """
        Sets the library folder path and generates a set of available and valid track paths in the folder.
        Skips settings if the given value is None.
        """
        if value is None:
            return
        self._library_folder: str = value.rstrip("\\/")
        self._track_paths = None
        if value is not None:
            self._track_paths = {path for c in __TRACK_CLASSES__ for path in c.get_filepaths(self._library_folder)}

        self.logger.debug(f"Set library folder: {self.library_folder} | {len(self._track_paths)} track paths found")

    @property
    def playlist_folder(self) -> str:
        """Path to the playlist folder"""
        return self._playlist_folder

    @playlist_folder.setter
    def playlist_folder(self, value: str | None):
        """
        Sets the playlist folder path and generates a set of available and valid playlists in the folder.
        Appends the library folder path if the given path is not valid. Skips settings if the given value is None.
        """
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
                entry = {
                    splitext(basename(path.replace(self._playlist_folder, "").lower()))[0]: path
                    for path in paths
                }
                playlists |= entry

            playlists_total = len(playlists)
            self._playlist_paths = {
                name: path for name, path in sorted(playlists.items(), key=lambda x: x[0])
                if (not self.include or name in self.include) and (not self.exclude or name not in self.exclude)
            }

            self.logger.debug(
                f"Filtered out {playlists_total - len(self._playlist_paths)} playlists "
                f"from {playlists_total} Spotify playlists"
            )

        self.logger.debug(f"Set playlist folder: {self.library_folder} | {len(self._track_paths)} playlists found")

    @property
    def name(self) -> str | None:
        """The basename of the library folder"""
        return basename(self.library_folder) if self.library_folder else None

    @property
    def playlists(self) -> dict[str, LocalPlaylist]:
        """The playlists in this library mapped as ``{name: playlist}``"""
        return self._playlists

    @property
    def folders(self) -> list[LocalFolder]:
        """Dynamically generate a set of folder collections from the tracks in this library"""
        grouped = TrackSorter.group_by_field(tracks=self.tracks, field=PropertyName.FOLDER)
        collections = [LocalFolder(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    @property
    def albums(self) -> list[LocalAlbum]:
        """Dynamically generate a set of album collections from the tracks in this library"""
        grouped = TrackSorter.group_by_field(tracks=self.tracks, field=TagName.ALBUM)
        collections = [LocalAlbum(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    @property
    def artists(self) -> list[LocalArtist]:
        """Dynamically generate a set of artist collections from the tracks in this library"""
        grouped = TrackSorter.group_by_field(tracks=self.tracks, field=TagName.ARTIST)
        collections = [LocalArtist(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    @property
    def genres(self) -> list[LocalGenres]:
        """Dynamically generate a set of genre collections from the tracks in this library"""
        grouped = TrackSorter.group_by_field(tracks=self.tracks, field=TagName.GENRES)
        collections = [LocalGenres(group, name=name) for name, group in grouped.items()]
        return sorted(collections, key=lambda x: x.name)

    def __init__(
            self,
            library_folder: str | None = None,
            playlist_folder: str | None = None,
            other_folders: UnitCollection[str] | None = None,
            include: Iterable[str] | None = None,
            exclude: Iterable[str] | None = None,
            load: bool = True,
    ):
        if not getattr(self, "logger", None):
            Logger.__init__(self)
        Library.__init__(self)

        self.include = [name.strip().lower() for name in include] if include else None
        self.exclude = [name.strip().lower() for name in exclude] if exclude else None

        self._library_folder: str | None = None
        # name of track object to set of paths valid for that track object
        self._track_paths: set[str] | None = None
        self.library_folder = library_folder

        self._playlist_folder: str | None = None
        # playlist lowercase name mapped to its filepath for all accepted filetypes in playlist folder
        self._playlist_paths: dict[str, str] | None = None
        self.playlist_folder: str | None = playlist_folder

        self.other_folders: UnitCollection[str] | None = other_folders

        self._tracks: list[LocalTrack] = []
        self._playlists: dict[str, LocalPlaylist] = {}

        if load:
            self.load()

    def load(self, tracks: bool = True, playlists: bool = True, log: bool = True) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self.logger.debug("Load local library: START")
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Loading local library of "
            f"{len(self._track_paths)} tracks and {len(self._playlist_paths)} playlists \33[0m"
        )
        self.print_line()

        if tracks:
            self._tracks = self.load_tracks()
            if log:
                self.log_tracks()

        if playlists:
            self._playlists = {pl.name: pl for pl in sorted(self.load_playlists(), key=lambda pl: pl.name.casefold())}
            if log:
                self.log_playlists()

        self.logger.debug("Load local library: DONE\n")

    def load_tracks(self) -> list[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        return self._load_tracks()

    def _load_tracks(self) -> list[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        self.logger.debug("Load local tracks: START")
        self.logger.info(
            f"\33[1;95m  >\33[1;97m "
            f"Extracting metadata and properties for {len(self._track_paths)} tracks \33[0m"
        )

        tracks: list[LocalTrack] = []
        errors: list[str] = []
        for path in self.get_progress_bar(iterable=self._track_paths, desc="Loading tracks", unit="tracks"):
            # noinspection PyBroadException
            try:
                tracks.append(load_track(path=path, available=self._track_paths))
            except Exception:
                errors.append(path)
                continue

        self.print_line()
        self._log_errors(errors)
        self.logger.debug("Load local tracks: DONE\n")
        return tracks

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        width = self.get_max_width(self._playlist_paths)
        self.logger.report(
            f"\33[1;96m{'LIBRARY URIS':<{width}}\33[1;0m |"
            f"\33[92m{sum([track.has_uri is True for track in self.tracks]):>6} available \33[0m|"
            f"\33[91m{sum([track.has_uri is None for track in self.tracks]):>6} missing \33[0m|"
            f"\33[93m{sum([track.has_uri is False for track in self.tracks]):>6} unavailable \33[0m|"
            f"\33[1;94m{len(self.tracks):>6} total \33[0m"
        )
        self.print_line(REPORT)

    def load_playlists(self, names: Collection[str] | None = None) -> list[LocalPlaylist]:
        """
        Load a playlist from a given list of names or, if None, load all playlists found in this library's loaded paths.
        The name must be relative to the playlist folder of this library and exist in its loaded paths.

        :param names: Playlist paths to load relative to the playlist folder.
        :return: The loaded playlists.
        :raises LocalCollectionError: If a given playlist name cannot be found.
        """
        self.logger.debug("Load local playlist data: START")
        if names is None:
            names = self._playlist_paths.keys()

        self.logger.info(f"\33[1;95m  >\33[1;97m Loading playlist data for {len(names)} playlists \33[0m")

        playlists: list[LocalPlaylist] = []
        errors: list[str] = []
        for name in self.get_progress_bar(iterable=names, desc="Loading playlists", unit="playlists"):
            path = self._playlist_paths.get(name.strip().lower())
            if path is None:
                raise LocalCollectionError(
                    f"Playlist name not found in the stored paths of this manager: {name}", kind="playlist"
                )

            ext = splitext(path)[1].lower()
            if ext in M3U.valid_extensions:
                pl = M3U(
                    path=path,
                    tracks=self.tracks,
                    library_folder=self.library_folder,
                    other_folders=self.other_folders,
                    available_track_paths=self._track_paths,
                )
            elif ext in XAutoPF.valid_extensions:
                pl = XAutoPF(
                    path=path,
                    tracks=self.tracks,
                    library_folder=self.library_folder,
                    other_folders=self.other_folders,
                    available_track_paths=self._track_paths,
                )
            else:
                raise IllegalFileTypeError(ext)

            playlists.append(pl)

        self.print_line()
        self._log_errors(errors)
        self.logger.debug("Load local playlist data: DONE\n")
        return playlists

    def save_playlists(self, dry_run: bool = True) -> dict[str, Result]:
        """Saves the tags of all tracks in this library. Use arguments from :py:func:`LocalPlaylist.save()`"""
        return {name: pl.save(dry_run=dry_run) for name, pl in self.playlists.items()}

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = self.get_max_width(self.playlists)

        self.logger.report("\33[1;96mFound the following local playlists: \33[0m")
        for name, playlist in self.playlists.items():
            self.logger.report(
                f"\33[97m{self.align_and_truncate(name, max_width=max_width)} \33[0m|"
                f"\33[92m{len([t for t in playlist if t.has_uri]):>6} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t.has_uri is None]):>6} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t.has_uri is False]):>6} unavailable \33[0m|"
                f"\33[1;94m{len(playlist):>6} total \33[0m"
            )
        self.print_line(REPORT)

    def _log_errors(self, errors: Iterable[str]) -> None:
        """Log paths which had some error while loading"""
        errors = tuple(f"\33[91m{e}\33[0m" for e in errors)
        if len(errors) > 0:
            self.logger.warning("\33[97mCould not load: \33[0m\n\t- {errors} ".format(errors="\n\t- ".join(errors)))
            self.print_line()

    def extend(self, items: Iterable[Item]):
        self.tracks.extend(track for track in items if isinstance(track, LocalTrack) and track not in self.tracks)

    def merge_playlists(self, playlists: Library | Collection[Playlist] | Mapping[Any, Playlist] | None = None):
        raise NotImplementedError

    def restore_tracks(
            self, backup: Mapping[str, Mapping[str, Any]], tags: UnitIterable[TagName] = TagName.ALL
    ) -> int:
        """
        Restore track tags from a backup to loaded track objects. This does not save the updated tags.

        :param backup: Backup data in the form ``{path: {JSON formatted track data}}``
        :param tags: Set of tags to restore.
        :returns: The number of tracks restored
        """
        tag_names = set(TagName.to_tags(tags))
        backup = {path.lower(): track_map for path, track_map in backup.items()}

        count = 0
        for track in self.tracks:
            track_map = backup.get(track.path.lower())
            if not track_map:
                continue

            for tag in tag_names:
                track[tag] = track_map.get(tag)
            count += 1

        return count

    def as_dict(self):
        return {
            "library_folder": self.library_folder,
            "playlists_folder": self.playlist_folder,
            "other_folders": self.other_folders,
            "track_count": len(self.tracks),
            "playlist_counts": {name: len(pl) for name, pl in self._playlists.items()},
        }

    def as_json(self):
        return {
            "library_folder": self.library_folder,
            "playlists_folder": self.playlist_folder,
            "other_folders": self.other_folders,
            "tracks": dict(sorted(((track.path, track.as_json()) for track in self.tracks), key=lambda x: x[0])),
            "playlists": {name: [tr.path for tr in pl] for name, pl in self.playlists.items()},
        }
