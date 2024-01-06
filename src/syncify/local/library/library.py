from collections.abc import Collection, Mapping, Iterable
from glob import glob
from os.path import splitext, join, exists, basename
from typing import Any

from syncify.shared.core.misc import Result, Filter
from syncify.shared.core.object import Playlist, Library
from syncify.shared.exception import SyncifyError
from syncify.local.track.fields import LocalTrackField
from syncify.local.collection import LocalCollection, LocalFolder, LocalAlbum, LocalArtist, LocalGenres
from syncify.local.exception import LocalCollectionError
from syncify.local.playlist import PLAYLIST_FILETYPES, LocalPlaylist, load_playlist
from syncify.local.track import TRACK_CLASSES, LocalTrack, load_track
from syncify.processors.sort import ItemSorter
from syncify.shared.remote.processors.wrangle import RemoteDataWrangler
from syncify.shared.types import UnitCollection, UnitIterable
from syncify.shared.utils import align_and_truncate, get_max_width, correct_platform_separators
from syncify.shared.logger import REPORT


class LocalLibrary(LocalCollection[LocalTrack], Library[LocalTrack]):
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
    :param include: An optional list or :py:class:`Filter` of playlist names to include when loading playlists.
    :param exclude: An optional list or :py:class:`Filter` of playlist names to exclude when loading playlists.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    __slots__ = (
        "_library_folder",
        "_playlist_folder",
        "other_folders",
        "include",
        "exclude",
        "_playlist_paths",
        "_playlists",
        "_track_paths",
        "_tracks",
    )

    # noinspection PyTypeChecker,PyPropertyDefinition
    @classmethod
    @property
    def name(cls) -> str:
        """The type of library loaded"""
        return cls.source

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def source(cls) -> str:
        """The type of local library loaded"""
        return cls.__name__.replace("Library", "")

    @property
    def tracks(self) -> list[LocalTrack]:
        """The tracks in this collection"""
        return self._tracks

    @property
    def playlists(self) -> dict[str, LocalPlaylist]:
        """The playlists in this library mapped as ``{name: playlist}``"""
        return self._playlists

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
        self._track_paths = set()
        if value is not None:
            self._track_paths = {path for c in TRACK_CLASSES for path in c.get_filepaths(self._library_folder)}

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

        playlists = {}
        for filetype in PLAYLIST_FILETYPES:
            paths = glob(join(self._playlist_folder, "**", f"*{filetype}"), recursive=True)
            entry = {
                splitext(basename(path.removeprefix(self._playlist_folder)))[0]: path
                for path in paths
            }
            playlists |= entry

        if isinstance(self.include, Filter):
            include = {name.casefold() for name in self.include.process(playlists.keys())} if self.include.ready else {}
        else:
            include = {name.strip().casefold() for name in self.include}
        if isinstance(self.exclude, Filter):
            exclude = {name.casefold() for name in self.exclude.process(playlists.keys())} if self.exclude.ready else {}
        else:
            exclude = {name.strip().casefold() for name in self.exclude}

        playlists_total = len(playlists)
        self._playlist_paths = {
            name.casefold(): path for name, path in sorted(playlists.items(), key=lambda x: x[0])
            if (not include or name.casefold() in include) and (not exclude or name.casefold() not in exclude)
        }

        log = (
            f"Filtered out {playlists_total - len(self._playlist_paths)} playlists "
            f"from {playlists_total} {self.name} playlists"
        ) if include or exclude else f"{len(self._playlist_paths)} playlists found"

        self.logger.debug(f"Set playlist folder: {self.playlist_folder} | {log}")

    @property
    def folders(self) -> list[LocalFolder]:
        """Dynamically generate a set of folder collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.FOLDER)
        collections = [
            LocalFolder(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items()
        ]
        return sorted(collections, key=lambda x: x.name)

    @property
    def albums(self) -> list[LocalAlbum]:
        """Dynamically generate a set of album collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.ALBUM)
        collections = [
            LocalAlbum(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items()
        ]
        return sorted(collections, key=lambda x: x.name)

    @property
    def artists(self) -> list[LocalArtist]:
        """Dynamically generate a set of artist collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.ARTIST)
        collections = [
            LocalArtist(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items()
        ]
        return sorted(collections, key=lambda x: x.name)

    @property
    def genres(self) -> list[LocalGenres]:
        """Dynamically generate a set of genre collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.GENRES)
        collections = [
            LocalGenres(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items()
        ]
        return sorted(collections, key=lambda x: x.name)

    def __init__(
            self,
            library_folder: str | None = None,
            playlist_folder: str | None = None,
            other_folders: UnitCollection[str] = (),
            include: Iterable[str] | Filter[str] = (),
            exclude: Iterable[str] | Filter[str] = (),
            remote_wrangler: RemoteDataWrangler | None = None,
    ):
        super().__init__(remote_wrangler=remote_wrangler)

        library_folder = correct_platform_separators(library_folder)
        playlist_folder = correct_platform_separators(playlist_folder)

        log_name = basename(library_folder) if library_folder and self.__class__ == LocalLibrary else self.name
        self.logger.debug(f"Setup {self.name} library: START")
        self.logger.info(f"\33[1;95m ->\33[1;97m Setting up {log_name} library \33[0m")
        self.logger.print()

        self.include = include
        self.exclude = exclude

        self._library_folder: str | None = None
        # name of track object to set of paths valid for that track object
        self._track_paths: set[str] = set()
        self.library_folder = library_folder

        self._playlist_folder: str | None = None
        # playlist lowercase name mapped to its filepath for all accepted filetypes in playlist folder
        self._playlist_paths: dict[str, str] | None = None
        self.playlist_folder: str | None = playlist_folder

        self.other_folders: UnitCollection[str] = other_folders

        self._tracks: list[LocalTrack] = []
        self._playlists: dict[str, LocalPlaylist] = {}

        self.errors: list[str] = []
        self.logger.debug(f"Setup {self.name} library: DONE\n")

    def load(self, tracks: bool = True, playlists: bool = True) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self.logger.debug(f"Load {self.name} library: START")
        log_types = [
            f"{len(self._track_paths or [])} tracks" * tracks,
            f"{len(self._playlist_paths or [])} playlists" * playlists
        ]
        log_types = " and ".join(log_type for log_type in log_types if log_type)
        self.logger.info(f"\33[1;95m ->\33[1;97m Loading {self.name} library of {log_types} \33[0m")

        if tracks:
            self._tracks = self.load_tracks()
            self.logger.print(REPORT)
            self.log_tracks()

        if playlists:
            self._playlists = {pl.name: pl for pl in sorted(self.load_playlists(), key=lambda pl: pl.name.casefold())}
            self.logger.print(REPORT)
            self.log_playlists()

        self.logger.print()
        self.logger.debug(f"Load {self.name} library: DONE\n")

    def load_tracks(self) -> list[LocalTrack]:
        """Returns a list of loaded tracks from all the valid paths in this library"""
        self.logger.debug(f"Load {self.name} tracks: START")
        self.logger.info(
            f"\33[1;95m  >\33[1;97m "
            f"Extracting metadata and properties for {len(self._track_paths)} tracks \33[0m"
        )

        tracks: list[LocalTrack] = []
        bar: Iterable[str] = self.logger.get_progress_bar(
            iterable=self._track_paths, desc="Loading tracks", unit="tracks"
        )
        for path in bar:
            try:
                tracks.append(load_track(path=path, available=self._track_paths, remote_wrangler=self.remote_wrangler))
            except SyncifyError:
                self.errors.append(path)
                continue

        self._log_errors()
        self.logger.debug(f"Load {self.name} tracks: DONE\n")
        return tracks

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        width = get_max_width(self._playlist_paths) if self._playlist_paths else 20
        self.logger.report(
            f"\33[1;96m{'LIBRARY URIS':<{width}}\33[1;0m |"
            f"\33[92m{sum([track.has_uri is True for track in self.tracks]):>6} available \33[0m|"
            f"\33[91m{sum([track.has_uri is None for track in self.tracks]):>6} missing \33[0m|"
            f"\33[93m{sum([track.has_uri is False for track in self.tracks]):>6} unavailable \33[0m|"
            f"\33[1;94m{len(self.tracks):>6} total \33[0m"
        )
        self.logger.print(REPORT)

    def load_playlists(self, names: Collection[str] | None = None) -> list[LocalPlaylist]:
        """
        Load a playlist from a given list of names or, if None, load all playlists found in this library's loaded paths.
        The name must be relative to the playlist folder of this library and exist in its loaded paths.

        :param names: Playlist paths to load relative to the playlist folder.
        :return: The loaded playlists.
        :raise LocalCollectionError: If a given playlist name cannot be found.
        """
        if not self._playlist_paths:
            return []

        self.logger.debug(f"Load {self.name} playlist data: START")
        if names is None:
            names = self._playlist_paths.keys()

        self.logger.info(f"\33[1;95m  >\33[1;97m Loading playlist data for {len(names)} playlists \33[0m")

        playlists: list[LocalPlaylist] = []
        bar: Iterable[str] = self.logger.get_progress_bar(iterable=names, desc="Loading playlists", unit="playlists")
        for name in bar:
            path = self._playlist_paths.get(name.strip().casefold())
            if path is None:
                raise LocalCollectionError(
                    f"Playlist name not found in the stored paths of this manager: {name}", kind="playlist"
                )

            pl = load_playlist(
                path=path,
                tracks=self.tracks,
                library_folder=self.library_folder,
                other_folders=self.other_folders,
                available_track_paths=self._track_paths,
                remote_wrangler=self.remote_wrangler,
            )

            playlists.append(pl)

        # self._log_errors()
        self.logger.debug(f"Load {self.name} playlist data: DONE\n")
        return playlists

    def save_playlists(self, dry_run: bool = True) -> dict[str, Result]:
        """
        For each Playlist in this Library, saves its associate tracks and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: A map of the playlist name to the results of its sync as a :py:class:`Result` object.
        """
        return {name: pl.save(dry_run=dry_run) for name, pl in self.playlists.items()}

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = get_max_width(self.playlists)

        self.logger.report(f"\33[1;96m{self.name.upper()} PLAYLISTS: \33[0m")
        for name, playlist in self.playlists.items():
            self.logger.report(
                f"\33[97m{align_and_truncate(name, max_width=max_width)} \33[0m|"
                f"\33[92m{len([t for t in playlist if t.has_uri]):>6} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t.has_uri is None]):>6} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t.has_uri is False]):>6} unavailable \33[0m|"
                f"\33[1;94m{len(playlist):>6} total \33[0m"
            )
        self.logger.print(REPORT)

    def _log_errors(self, message: str = "Could not load") -> None:
        """Log paths which had some error while loading"""
        errors = tuple(f"\33[91m{e}\33[0m" for e in self.errors)
        if len(errors) > 0:
            self.logger.warning(f"\33[97m{message}: \33[0m\n\t- {"\n\t- ".join(errors)} ")
            self.logger.print()
        self.errors.clear()

    def merge_playlists(self, playlists: Library | Collection[Playlist] | Mapping[Any, Playlist]) -> None:
        raise NotImplementedError

    def restore_tracks(
            self, backup: Mapping[str, Mapping[str, Any]], tags: UnitIterable[LocalTrackField] = LocalTrackField.ALL
    ) -> int:
        """
        Restore track tags from a backup to loaded track objects. This does not save the updated tags.

        :param backup: Backup data in the form ``{path: {JSON formatted track data}}``
        :param tags: Set of tags to restore.
        :return: The number of tracks restored
        """
        tag_names = set(LocalTrackField.to_tags(tags))
        backup = {path.casefold(): track_map for path, track_map in backup.items()}

        count = 0
        for track in self.tracks:
            track_map = backup.get(track.path.casefold())
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
            "remote_source": self.remote_wrangler.source if self.remote_wrangler else None,
        }

    def json(self):
        return {
            "library_folder": self.library_folder,
            "playlists_folder": self.playlist_folder,
            "other_folders": self.other_folders,
            "tracks": dict(sorted(((track.path, track.json()) for track in self.tracks), key=lambda x: x[0])),
            "playlists": {name: [tr.path for tr in pl] for name, pl in self.playlists.items()},
        }
