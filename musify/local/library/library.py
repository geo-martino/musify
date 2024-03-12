"""
The core, basic library implementation which is just a simple set of folders.
"""
import itertools
from collections.abc import Collection, Mapping, Iterable
from functools import reduce
from os.path import splitext, join, exists, basename, dirname
from typing import Any

from musify.local.collection import LocalCollection, LocalFolder, LocalAlbum, LocalArtist, LocalGenres
from musify.local.file import PathMapper, PathStemMapper
from musify.local.playlist import LocalPlaylist, load_playlist, PLAYLIST_CLASSES
from musify.local.track import TRACK_CLASSES, LocalTrack, load_track
from musify.local.track.field import LocalTrackField
from musify.processors.base import Filter
from musify.processors.filter import FilterDefinedList
from musify.processors.sort import ItemSorter
from musify.shared.core.misc import Result
from musify.shared.core.object import Playlist, Library
from musify.shared.exception import MusifyError
from musify.shared.logger import STAT
from musify.shared.remote.processors.wrangle import RemoteDataWrangler
from musify.shared.types import UnitCollection, UnitIterable
from musify.shared.utils import align_string, get_max_width, to_collection


class LocalLibrary(LocalCollection[LocalTrack], Library[LocalTrack]):
    """
    Represents a local library, providing various methods for manipulating
    tracks and playlists across an entire local library collection.

    :param library_folders: The absolute paths of the library folders containing all tracks.
        The intialiser will check for the existence of these paths and only store them if they exist.
    :param playlist_folder: The absolute path of the playlist folder containing all playlists
        or the relative path within one of the available ``library_folders``.
        If a relative path is given and many library folders are given,
        only the first path that gives an existing result is processed.
        The setter will check for the existence of this path and only store the absolute path if it exists.
    :param playlist_filter: An optional :py:class:`Filter` to apply or collection of playlist names to include when
        loading playlists. Playlist names will be passed to this filter to limit which playlists are loaded.
    :param path_mapper: Optionally, provide a :py:class:`PathMapper` for paths stored in the playlist files.
        Useful if the playlist files contain relative paths and/or paths for other systems that need to be
        mapped to absolute, system-specific paths to be loaded and back again when saved.
    :param remote_wrangler: Optionally, provide a :py:class:`RemoteDataWrangler` object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    __slots__ = (
        "_library_folders",
        "_playlist_folder",
        "playlist_filter",
        "path_mapper",
        "_playlist_paths",
        "_playlists",
        "_track_paths",
        "_tracks",
    )
    __attributes_classes__ = (Library, LocalCollection)

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
        """The playlists in this library mapped as ``{<name>: <playlist>}``"""
        return self._playlists

    @property
    def library_folders(self) -> list[str]:
        """Path to the library folder"""
        return self._library_folders

    @library_folders.setter
    def library_folders(self, value: UnitCollection[str] | None):
        """
        Sets the library folder path and generates a set of available and valid track paths in the folder.
        Skips settings if the given value is None.
        """
        if value is None:
            return

        folders = [v.rstrip("\\/") for v in to_collection(value)]
        self._library_folders: list[str] = [folder for folder in folders if exists(folder)]

        self._track_paths = {
            path for folder in self._library_folders for cls in TRACK_CLASSES for path in cls.get_filepaths(folder)
        }
        if isinstance(self.path_mapper, PathStemMapper):
            self.path_mapper.available_paths = self._track_paths

        self.logger.debug(
            f"Set library folder(s): {", ".join(self.library_folders)} | {len(self._track_paths)} track paths found"
        )

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
        if not exists(value) and self.library_folders:
            for folder in self.library_folders:
                value = join(folder, value.lstrip("\\/"))
                if exists(value):
                    break
        if not exists(value):
            return

        self._playlist_folder: str = value.rstrip("\\/")
        self._playlist_paths = None

        playlists = {
            splitext(basename(path.removeprefix(self._playlist_folder)))[0]: path
            for cls in PLAYLIST_CLASSES for path in cls.get_filepaths(self._playlist_folder)
        }

        pl_total = len(playlists)
        pl_filtered = self.playlist_filter(playlists)
        self._playlist_paths = {
            name: path for name, path in sorted(playlists.items(), key=lambda x: x[0].casefold())
            if name in pl_filtered
        }

        self.logger.debug(f"Set playlist folder: {self.playlist_folder} | " + (
            f"Filtered out {pl_total - len(self._playlist_paths)} playlists "
            f"from {pl_total} {self.name} available playlists"
            if (pl_total - len(pl_filtered)) > 0 else f"{len(self._playlist_paths)} playlists found"
        ))

    @property
    def folders(self) -> list[LocalFolder]:
        """
        Dynamically generate a set of folder collections from the tracks in this library.
        Folder collections are generated relevant to the library folder it is found in.
        """
        def get_relative_path(track: LocalTrack) -> str:
            """Return path of a track relative to the library folders of this library"""
            return dirname(reduce(
                lambda path, folder: path.replace(folder, ""), self.library_folders, track.path
            )).lstrip("\\/")

        def create_folder_collection(name: str, tracks: Collection[LocalTrack]) -> LocalFolder:
            """
            Create a :py:class:`LocalFolder` collection from the given ``tracks``,
            ensuring the collection has the exact given ``name``.
            """
            folder = LocalFolder(tracks=tracks, name=basename(name), remote_wrangler=self.remote_wrangler)
            folder._name = name
            return folder

        grouped = itertools.groupby(sorted(self.tracks, key=lambda track: track.path), get_relative_path)
        collections = [create_folder_collection(name=name, tracks=list(group)) for name, group in grouped if name]
        return sorted(collections, key=lambda x: x.name)

    @property
    def albums(self) -> list[LocalAlbum]:
        """Dynamically generate a set of album collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.ALBUM)
        collections = [
            LocalAlbum(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items() if name
        ]
        return sorted(collections, key=lambda x: x.name)

    @property
    def artists(self) -> list[LocalArtist]:
        """Dynamically generate a set of artist collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.ARTIST)
        collections = [
            LocalArtist(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items() if name
        ]
        return sorted(collections, key=lambda x: x.name)

    @property
    def genres(self) -> list[LocalGenres]:
        """Dynamically generate a set of genre collections from the tracks in this library"""
        grouped = ItemSorter.group_by_field(items=self.tracks, field=LocalTrackField.GENRES)
        collections = [
            LocalGenres(tracks=group, name=name, remote_wrangler=self.remote_wrangler)
            for name, group in grouped.items() if name
        ]
        return sorted(collections, key=lambda x: x.name)

    def __init__(
            self,
            library_folders: UnitCollection[str] | None = None,
            playlist_folder: str | None = None,
            playlist_filter: Collection[str] | Filter[str] = (),
            path_mapper: PathMapper = PathMapper(),
            remote_wrangler: RemoteDataWrangler | None = None,
    ):
        super().__init__(remote_wrangler=remote_wrangler)

        self.logger.debug(f"Setup {self.name} library: START")
        self.logger.info(f"\33[1;95m ->\33[1;97m Setting up {self.name} library \33[0m")
        self.logger.print()

        #: Passed to playlist objects when loading playlists to map paths stored in the playlist file.
        self.path_mapper = path_mapper

        self._library_folders: list[str] = []
        self._track_paths: set[str] = set()
        self.library_folders = library_folders

        if not isinstance(playlist_filter, Filter):
            playlist_filter = FilterDefinedList(playlist_filter)
        #: :py:class:`Filter` to filter out the playlists loaded by name.
        self.playlist_filter: Filter[str] = playlist_filter

        self._playlist_folder: str | None = None
        # playlist lowercase name mapped to its filepath for all accepted filetypes in playlist folder
        self._playlist_paths: dict[str, str] = {}
        self.playlist_folder: str | None = playlist_folder

        self._tracks: list[LocalTrack] = []
        self._playlists: dict[str, LocalPlaylist] = {}

        #: Stores the paths that caused errors when loading/enriching
        self.errors: list[str] = []
        self.logger.debug(f"Setup {self.name} library: DONE\n")

    def load(self) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self.logger.debug(f"Load {self.name} library: START")
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Loading {self.name} library of "
            f"{len(self._track_paths)} tracks and {len(self._playlist_paths)} playlists \33[0m"
        )

        self.load_tracks()
        self.load_playlists()

        self.logger.print(STAT)
        self.log_tracks()
        self.log_playlists()

        self.logger.print()
        self.logger.debug(f"Load {self.name} library: DONE\n")

    def _log_errors(self, message: str = "Could not load") -> None:
        """Log paths which had some error while loading"""
        errors = tuple(f"\33[91m{e}\33[0m" for e in self.errors)
        if len(errors) > 0:
            self.logger.warning(f"\33[97m{message}: \33[0m\n\t- {"\n\t- ".join(errors)} ")
            self.logger.print()
        self.errors.clear()

    ###########################################################################
    ## Tracks
    ###########################################################################
    def load_tracks(self) -> None:
        """Load all tracks from all the valid paths in this library, replacing currently loaded tracks."""
        self.logger.debug(f"Load {self.name} tracks: START")
        self.logger.info(
            f"\33[1;95m  >\33[1;97m Extracting metadata and properties for {len(self._track_paths)} tracks \33[0m"
        )

        tracks: list[LocalTrack] = []
        bar: Iterable[str] = self.logger.get_progress_bar(
            iterable=self._track_paths, desc="Loading tracks", unit="tracks"
        )
        for path in bar:
            try:
                tracks.append(load_track(path=path, remote_wrangler=self.remote_wrangler))
            except MusifyError as ex:
                self.logger.debug(f"Load error: {path} - {ex}")
                self.errors.append(path)
                continue

        self._tracks = tracks
        self._log_errors()
        self.logger.debug(f"Load {self.name} tracks: DONE\n")

    def log_tracks(self) -> None:
        width = get_max_width(self._playlist_paths) if self._playlist_paths else 20
        self.logger.stat(
            f"\33[1;96m{'LIBRARY URIS':<{width}}\33[1;0m |"
            f"\33[92m{sum([track.has_uri is True for track in self.tracks]):>6} available \33[0m|"
            f"\33[91m{sum([track.has_uri is None for track in self.tracks]):>6} missing \33[0m|"
            f"\33[93m{sum([track.has_uri is False for track in self.tracks]):>6} unavailable \33[0m|"
            f"\33[1;94m{len(self.tracks):>6} total \33[0m"
        )

    ###########################################################################
    ## Playlists
    ###########################################################################
    def load_playlists(self) -> None:
        """
        Load all playlists found in this library's ``playlist_folder``,
        filtered down using the ``playlist_filter`` if given, replacing currently loaded playlists.

        :return: The loaded playlists.
        :raise LocalCollectionError: If a given playlist name cannot be found.
        """
        if not self._playlist_paths:
            return

        self.logger.debug(f"Load {self.name} playlist data: START")
        self.logger.info(
            f"\33[1;95m  >\33[1;97m Loading playlist data for {len(self._playlist_paths)} playlists \33[0m"
        )

        iterable = self._playlist_paths.items()
        bar = self.logger.get_progress_bar(iterable=iterable, desc="Loading playlists", unit="playlists")
        playlists: list[LocalPlaylist] = [
            load_playlist(
                path=path, tracks=self.tracks, path_mapper=self.path_mapper, remote_wrangler=self.remote_wrangler,
            ) for name, path in bar
        ]

        self._playlists = {pl.name: pl for pl in sorted(playlists, key=lambda x: x.name.casefold())}
        self.logger.debug(f"Load {self.name} playlists: DONE\n")

    def log_playlists(self) -> None:
        max_width = get_max_width(self.playlists)

        self.logger.stat(f"\33[1;96m{self.name.upper()} PLAYLISTS: \33[0m")
        for name, playlist in self.playlists.items():
            self.logger.stat(
                f"\33[97m{align_string(name, max_width=max_width)} \33[0m|"
                f"\33[92m{len([t for t in playlist if t.has_uri]):>6} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t.has_uri is None]):>6} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t.has_uri is False]):>6} unavailable \33[0m|"
                f"\33[1;94m{len(playlist):>6} total \33[0m"
            )

    def save_playlists(self, dry_run: bool = True) -> dict[str, Result]:
        """
        For each Playlist in this Library, saves its associate tracks and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: A map of the playlist name to the results of its sync as a :py:class:`Result` object.
        """
        return {name: pl.save(dry_run=dry_run) for name, pl in self.playlists.items()}

    def merge_playlists(
            self, playlists: Library[LocalTrack] | Collection[Playlist[LocalTrack]] | Mapping[Any, Playlist[LocalTrack]]
    ) -> None:
        raise NotImplementedError

    ###########################################################################
    ## Backup/restore
    ###########################################################################
    def restore_tracks(
            self, backup: Mapping[str, Mapping[str, Any]], tags: UnitIterable[LocalTrackField] = LocalTrackField.ALL
    ) -> int:
        """
        Restore track tags from a backup to loaded track objects. This does not save the updated tags.

        :param backup: Backup data in the form ``{<path>: {<Map of JSON formatted track data>}}``
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
                if tag in track.__dict__:
                    track[tag] = track_map.get(tag)
            count += 1

        return count

    def _get_attributes(self) -> dict[str, Any]:
        attributes_extra = {"remote_source": self.remote_wrangler.source if self.remote_wrangler else None}
        return super()._get_attributes() | attributes_extra
