from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping, Iterable
from typing import Any, Literal

from syncify.abstract.collection import Library, Playlist
from syncify.abstract.item import Item, Track
from syncify.remote.api import RemoteAPI
from syncify.remote.config import RemoteObjectClasses
from syncify.remote.library.collection import SyncResultRemotePlaylist, RemotePlaylist, RemoteCollection
from syncify.remote.library.item import RemoteTrack
from syncify.remote.library.object import RemoteObject
from syncify.utils.logger import REPORT, STAT


# noinspection PyShadowingNames
class RemoteLibrary[T: RemoteTrack](Library[T], RemoteCollection[T], metaclass=ABCMeta):
    """
    Represents a remote library, providing various methods for manipulating
    tracks and playlists across an entire remote library collection.

    :param api: An authorised API object for the authenticated user you wish to load the library from.
    :param include: An optional list of playlist names to include when loading playlists.
    :param exclude: An optional list of playlist names to exclude when loading playlists.
    :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
    """

    __slots__ = ("_api", "_tracks", "_playlists", "include", "exclude", "use_cache")

    @property
    @abstractmethod
    def _remote_types(self) -> RemoteObjectClasses:
        raise NotImplementedError

    @property
    def name(self):
        """The username associated with this library"""
        return self.api.user_name

    @property
    def id(self):
        """The user ID associated with this library"""
        return self.api.user_id

    @property
    def tracks(self) -> list[T]:
        return self._tracks

    @property
    def playlists(self) -> dict[str, RemotePlaylist]:
        return self._playlists

    @property
    def api(self) -> RemoteAPI:
        """Authorised API object for making authenticated calls to a user's library"""
        return self._api

    def __init__(
            self, api: RemoteAPI, include: Iterable[str] = (), exclude: Iterable[str] = (), use_cache: bool = True,
    ):
        super().__init__()

        self._api = api
        self.include = include
        self.exclude = exclude
        self.use_cache = use_cache
        RemoteObject.api = api

        self._tracks: list[T] = []
        self._playlists: dict[str, RemotePlaylist] = {}

    def load(self, log: bool = True, **__) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self.logger.debug(f"Load {self.remote_source} library: START")
        self.api.load_user_data()

        self.logger.info(f"\33[1;95m ->\33[1;97m Loading {self.remote_source} library \33[0m")
        self.print_line()

        # get raw API responses
        playlists_data = self._get_playlists_data()
        tracks_data = self._get_tracks_data(playlists_data=playlists_data)

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Processing {self.remote_source} library of "
            f"{len(tracks_data)} tracks and {len(playlists_data)} playlists \33[0m"
        )
        track_bar = self.get_progress_bar(iterable=tracks_data, desc="Processing tracks", unit="tracks")
        playlists_bar = self.get_progress_bar(iterable=playlists_data, desc="Processing playlists", unit="playlists")

        # process to remote objects
        self._tracks = list(map(self._remote_types.track, track_bar))
        playlists = [
            self._remote_types.playlist.load(pl, items=self.tracks, use_cache=self.use_cache)
            for pl in playlists_bar
        ]
        self._playlists = {pl.name: pl for pl in sorted(playlists, key=lambda pl: pl.name.casefold())}

        self.print_line()
        if log:
            self.log_playlists()
            self.log_tracks()

        self.logger.debug(f"Load {self.remote_source} library: DONE\n")

    def _get_playlists_data(self) -> list[dict[str, Any]]:
        """
        Get API responses for all playlists and all their tracks

        :return: A list of API responses for all playlists
            with all API responses for tracks information contained therein.
        """
        raise NotImplementedError

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = self.get_max_width(self.playlists)

        self.logger.report(f"\33[1;96mLoaded the following {self.remote_source} playlists: \33[0m")
        for name, playlist in self.playlists.items():
            name = self.align_and_truncate(playlist.name, max_width=max_width)
            self.logger.report(f"\33[97m{name} \33[0m| \33[92m{len(playlist):>6} total tracks \33[0m")
        self.print_line(REPORT)

    @abstractmethod
    def _get_tracks_data(self, playlists_data: Collection[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """
        Get a list API responses of unique tracks across all playlists

        :param playlists_data: Collection of API responses for playlists.
        :return: A unique list of API responses for all tracks across all given playlists.
        """
        raise NotImplementedError

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        playlist_tracks = [track.uri for tracks in self.playlists.values() for track in tracks]
        in_playlists = len([track for track in self.tracks if track.uri in playlist_tracks])

        width = self.get_max_width(self.playlists)
        self.logger.report(
            f"\33[1;96m{self.remote_source.upper() + ' ITEMS':<{width}}\33[1;0m |"
            f"\33[92m{in_playlists:>7} in playlists \33[0m|"
            f"\33[1;94m{len(self.tracks):>6} total \33[0m"
        )
        self.print_line(REPORT)

    def enrich_tracks(self, *args, **kwargs) -> None:
        """
        Call API to enrich elements of track objects improving metadata coverage.
        This is an optionally implementable method. Defaults to doing nothing.
        """
        self.logger.debug("Enrich tracks not implemented for this library, skipping...")

    def backup_playlists(self) -> dict[str, list[str]]:
        """
        Produce a backup map of <playlist name>: [<URIs] for all playlists in this library
        which can be saved to JSON for backup purposes.
        """
        return {name: [track.uri for track in pl] for name, pl in self.playlists.items()}

    def restore_playlists(
            self,
            playlists: Library | Collection[Playlist] | Mapping[str, Iterable[Track]] | Mapping[str, Iterable[str]]
    ) -> None:
        """
        Restore playlists from a backup to loaded playlist objects.

        This function does not sync the updated playlists with the remote library.

        This function does create new playlists on the remote library for playlists
        given that do not exist in this Library.

        :param playlists: Values that represent the playlists to restore from.
        """
        # TODO: expand this function to support all RemoteItem types + update input type
        if isinstance(playlists, Library):  # get URIs from playlists in library
            playlists = {name: [track.uri for track in pl] for name, pl in playlists.playlists.items()}
        elif isinstance(playlists, Mapping) and all(isinstance(v, Item) for vals in playlists.values() for v in vals):
            # get URIs from playlists in map values
            playlists = {name: [item.uri for item in pl] for name, pl in playlists.items()}
        elif not isinstance(playlists, Mapping) and isinstance(playlists, Collection):
            # get URIs from playlists in collection
            playlists = {pl.name: [track.uri for track in pl] for pl in playlists}
        playlists: Mapping[str, Iterable[str]]

        uri_tracks = {track.uri: track for track in self.tracks}
        uri_get = [uri for uri_list in playlists.values() for uri in uri_list if uri not in uri_tracks]

        if uri_get:
            tracks_data = self.api.get_tracks(uri_get, features=True, use_cache=self.use_cache)
            tracks = list(map(self._remote_types.track, tracks_data))
            uri_tracks |= {track.uri: track for track in tracks}

        for name, uri_list in playlists.items():
            playlist = self.playlists.get(name)
            if not playlist:  # new playlist given, create it on remote first
                playlist = self._remote_types.playlist.create(name=name)

            playlist._tracks = [uri_tracks.get(uri) for uri in uri_list]
            self.playlists[name] = playlist

    def sync(
            self,
            playlists: Library | Mapping[str, Iterable[Item]] | Collection[Playlist] | None = None,
            kind: Literal["new", "refresh", "sync"] = "new",
            reload: bool = True,
            dry_run: bool = True
    ) -> dict[str, SyncResultRemotePlaylist]:
        """
        Synchronise this playlist object with the remote playlist it is associated with. Clear options:

        * 'new': Do not clear any items from the remote playlist and only add any tracks
            from this playlist object not currently in the remote playlist.
        * 'refresh': Clear all items from the remote playlist first, then add all items from this playlist object.
        * 'sync': Clear all items not currently in this object's items list, then add all tracks
            from this playlist object not currently in the remote playlist.

        :param playlists: Provide a library, map of playlist name to playlist or collection of playlists
            to synchronise to the remote library.
            Use the currently loaded ``playlists`` in this object if not given.
        :param kind: Sync option for the remote playlist. See description.
        :param reload: When True, once synchronisation is complete, reload this RemotePlaylist object
            to reflect the changes on the remote playlist if enabled. Skip if False.
        :param dry_run: Run function, but do not modify the remote playlists at all.
        :return: Map of playlist name to the results of the sync as a :py:class:`SyncResultRemotePlaylist` object.
        """
        self.logger.debug(f"Sync {self.remote_source} playlists: START")

        if not playlists:  # use the playlists as stored in this library object
            playlists = self.playlists
        elif isinstance(playlists, Library):  # get map of playlists from the given library
            playlists = playlists.playlists
        elif isinstance(playlists, Collection) and all(isinstance(pl, Playlist) for pl in playlists):
            # reformat list to map
            playlists = {pl.name: pl for pl in playlists}
        playlists: Mapping[str, Iterable[Item]]

        log_kind = "adding new items only"
        if kind != "new":
            log_kind = f"clearing {'all' if kind == 'refresh' else 'extra'} items from syncify.remote playlist first"
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Synchronising {len(playlists)} {self.remote_source} playlists: {log_kind}"
            f"{f' and reloading stored playlists' if reload else ''} \33[0m"
        )

        bar = self.get_progress_bar(
            iterable=playlists.items(), desc=f"Synchronising {self.remote_source}", unit="playlists"
        )
        results = {}
        for name, pl in bar:  # synchronise playlists
            if name not in self.playlists:  # new playlist given, create it on remote first
                self.playlists[name] = self._remote_types.playlist.create(name=name)
            results[name] = self.playlists[name].sync(items=pl, kind=kind, reload=reload, dry_run=dry_run)

        self.print_line()
        self.logger.debug(f"Sync {self.remote_source} playlists: DONE\n")
        return results

    def log_sync(self, results: Mapping[str, SyncResultRemotePlaylist]) -> None:
        """Log stats from the results of a ``sync`` operation"""
        if not results:
            return

        max_width = self.get_max_width(self.playlists)

        self.logger.stat(f"\33[1;96mSync {self.remote_source} playlists' stats: \33[0m")
        for name, result in results.items():
            self.logger.stat(
                f"\33[97m{self.align_and_truncate(name, max_width=max_width)} \33[0m|"
                f"\33[96m{result.start:>6} initial \33[0m|"
                f"\33[92m{result.added:>6} added \33[0m|"
                f"\33[91m{result.removed:>6} removed \33[0m|"
                f"\33[93m{result.unchanged:>6} unchanged \33[0m|"
                f"\33[94m{result.difference:>6} difference \33[0m|"
                f"\33[1;97m{result.final:>6} final \33[0m"
            )
        self.print_line(STAT)

    def extend(self, __items: Iterable[Item], allow_duplicates: bool = True) -> None:
        self.logger.debug(f"Extend {self.remote_source} tracks data: START")
        if not allow_duplicates:
            self.logger.info(
                f"\33[1;95m ->\33[1;97m Extending library: "
                "checking if the given items are already in this library \33[0m"
            )

        load_uris = []
        for item in __items:
            if not allow_duplicates and item in self.items:
                continue
            elif isinstance(item, self._remote_types.track):
                self.items.append(item)
            elif item.has_uri:
                load_uris.append(item.uri)

        self.print_line()
        if not load_uris:
            return

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Extending {self.remote_source} library "
            f"with {len(load_uris)} additional tracks \33[0m"
        )

        load_tracks = self.api.get_tracks(load_uris, features=True, use_cache=self.use_cache)
        self.items.extend(self._remote_types.track(response) for response in load_tracks)

        self.print_line()
        self.log_tracks()
        self.logger.debug(f"Extend {self.remote_source} tracks data: DONE\n")

    def as_dict(self):
        return {
            "user_name": self.api.user_name,
            "user_id": self.api.user_id,
            "track_count": len(self.tracks),
            "playlist_counts": {name: len(pl) for name, pl in self.playlists.items()},
        }

    def json(self):
        return {
            "user_name": self.api.user_name,
            "user_id": self.api.user_id,
            "tracks": dict(sorted(((track.uri, track.json()) for track in self.tracks), key=lambda x: x[0])),
            "playlists": {name: [tr.uri for tr in pl] for name, pl in self.playlists.items()},
        }
