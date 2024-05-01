"""
Functionality relating to a generic remote library.
"""
from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping, Iterable
from typing import Any, Literal

from musify.core.base import MusifyItem
from musify.libraries.core.object import Track, Library, Playlist
from musify.libraries.remote.core.api import RemoteAPI
from musify.libraries.remote.core.enum import RemoteObjectType
from musify.libraries.remote.core.factory import RemoteObjectFactory
from musify.libraries.remote.core.object import RemoteCollection, SyncResultRemotePlaylist
from musify.libraries.remote.core.object import RemoteTrack, RemotePlaylist, RemoteArtist, RemoteAlbum
from musify.log import STAT
from musify.processors.base import Filter
from musify.processors.filter import FilterDefinedList
from musify.utils import align_string, get_max_width


class RemoteLibrary[
    A: RemoteAPI, PL: RemotePlaylist, TR: RemoteTrack, AL: RemoteAlbum, AR: RemoteArtist
](RemoteCollection[TR], Library[TR], metaclass=ABCMeta):
    """
    Represents a remote library, providing various methods for manipulating
    tracks and playlists across an entire remote library collection.

    :param api: The instantiated and authorised API object for this source type.
    :param playlist_filter: An optional :py:class:`Filter` to apply or collection of playlist names to include when
        loading playlists. Playlist names will be passed to this filter to limit which playlists are loaded.
    :param use_cache: Use the cache when calling the API endpoint.
        When using a CachedSession, set as False to refresh the cached response.
    """

    __slots__ = ("_factory", "_tracks", "_playlists", "playlist_filter")
    __attributes_classes__ = (Library, RemoteCollection)
    __attributes_ignore__ = ("api", "factory")

    @property
    def factory(self) -> RemoteObjectFactory[A, PL, TR, AL, AR]:
        """Stores the key object classes for a remote source."""
        return self._factory

    @abstractmethod
    def _create_factory(self, api: A) -> RemoteObjectFactory[A, PL, TR, AL, AR]:
        """Stores the key object classes for a remote source."""
        raise NotImplementedError

    @property
    def api(self):
        """Authorised API object for making authenticated calls to a user's library"""
        return self.factory.api

    @property
    def name(self):
        """The username associated with this library"""
        return self.api.user_name

    @property
    def id(self):
        """The user ID associated with this library"""
        return self.api.user_id

    @property
    def playlists(self) -> dict[str, PL]:
        return self._playlists

    @property
    def tracks(self) -> list[TR]:
        """All user's saved tracks"""
        return self._tracks

    @property
    def artists(self) -> list[AR]:
        """All user's saved artists"""
        return self._artists

    @property
    def albums(self) -> list[AL]:
        """All user's saved albums"""
        return self._albums

    def __init__(self, api: A, use_cache: bool = True, playlist_filter: Collection[str] | Filter[str] = ()):
        super().__init__(remote_wrangler=api.wrangler)

        #: When true, use the cache when calling the API endpoint
        self.use_cache = use_cache

        if not isinstance(playlist_filter, Filter):
            playlist_filter = FilterDefinedList(playlist_filter)
        #: :py:class:`Filter` to filter out the playlists loaded by name.
        self.playlist_filter: Filter[str] = playlist_filter

        self._factory = self._create_factory(api=api)
        self._playlists: dict[str, PL] = {}
        self._tracks: list[TR] = []
        self._albums: list[AL] = []
        self._artists: list[AR] = []

    def extend(self, __items: Iterable[MusifyItem], allow_duplicates: bool = True) -> None:
        self.logger.debug(f"Extend {self.api.source} tracks data: START")
        if not allow_duplicates:
            self.logger.info(
                "\33[1;95m ->\33[1;97m Extending library: "
                "checking if the given items are already in this library \33[0m"
            )

        load_uris = []
        bar = self.logger.get_progress_bar(iterable=__items, desc="Checking items", unit="items")
        for item in bar:
            if not allow_duplicates and item in self.items:
                continue
            elif isinstance(item, RemoteTrack):
                self.items.append(item)
            elif item.has_uri:
                load_uris.append(item.uri)

        if not load_uris:
            return

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Extending {self.api.source} library "
            f"with {len(load_uris)} additional tracks \33[0m"
        )

        load_tracks = self.api.get_tracks(load_uris, features=True, use_cache=self.use_cache)
        self.items.extend(map(self.factory.track, load_tracks))

        self.logger.print(STAT)
        self.log_tracks()
        self.logger.print()
        self.logger.debug(f"Extend {self.api.source} tracks data: DONE\n")

    def load(self) -> None:
        """Loads all data from the remote API for this library and log results."""
        self.logger.debug(f"Load {self.api.source} library: START")
        self.logger.info(f"\33[1;95m ->\33[1;97m Loading {self.api.source} library \33[0m")

        self.load_playlists()
        self.load_tracks()
        self.load_saved_albums()
        self.load_saved_artists()

        self.logger.print(STAT)
        self.log_playlists()
        self.log_tracks()
        self.log_albums()
        self.log_artists()

        self.logger.print()
        self.logger.debug(f"Load {self.api.source} library: DONE\n")

    ###########################################################################
    ## Load - playlists
    ###########################################################################
    def load_playlists(self) -> None:
        """
        Load all playlists from the API that match the filter rules in this library. Also loads all their tracks.
        WARNING: Overwrites any currently loaded playlists.
        """
        self.logger.debug(f"Load {self.api.source} playlists: START")
        self.api.load_user_data()

        responses = self.api.get_user_items(kind=RemoteObjectType.PLAYLIST, use_cache=self.use_cache)
        responses = self._filter_playlists(responses)

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Getting {self._get_total_tracks(responses=responses)} "
            f"{self.api.source} tracks from {len(responses)} playlists \33[0m"
        )
        self.api.get_items(responses, kind=RemoteObjectType.PLAYLIST, use_cache=self.use_cache)

        playlists = [
            self.factory.playlist(response=r, skip_checks=False)
            for r in self.logger.get_progress_bar(iterable=responses, desc="Processing playlists", unit="playlists")
        ]

        self._playlists = {pl.name: pl for pl in sorted(playlists, key=lambda x: x.name.casefold())}
        self.logger.debug(f"Load {self.api.source} playlists: DONE")

    def _filter_playlists(self, responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Filter API responses from all playlists according to filter rules in this library.

        :return: Filtered API responses.
        """
        raise NotImplementedError

    def _get_total_tracks(self, responses: list[dict[str, Any]]) -> int:
        """
        Returns the total number of tracks across all given playlists data. Used for logging purposes

        :return: Total track count.
        """
        raise NotImplementedError

    def log_playlists(self) -> None:
        max_width = get_max_width(self.playlists)

        self.logger.stat(f"\33[1;96m{self.api.source.upper()} PLAYLISTS: \33[0m")
        for name, playlist in self.playlists.items():
            name = align_string(playlist.name, max_width=max_width)
            self.logger.stat(f"\33[97m{name} \33[0m| \33[92m{len(playlist):>6} total tracks \33[0m")

    ###########################################################################
    ## Load - tracks
    ###########################################################################
    def load_tracks(self) -> None:
        """
        Load all user's saved tracks from the API.
        Updates currently loaded tracks in-place or appends if not already loaded.
        """
        self.logger.debug(f"Load user's saved {self.api.source} tracks: START")
        self.api.load_user_data()

        responses = self.api.get_user_items(kind=RemoteObjectType.TRACK, use_cache=self.use_cache)
        for response in self.logger.get_progress_bar(iterable=responses, desc="Processing tracks", unit="tracks"):
            track = self.factory.track(response=response, skip_checks=True)

            if not track.has_uri:  # skip any invalid non-remote responses
                continue

            current = next((item for item in self._tracks if item == track), None)
            if current is None:
                self._tracks.append(track)
            else:
                current._response = track.response
                current.refresh(skip_checks=False)

        self.logger.debug(f"Load user's saved {self.api.source} tracks: DONE")

    def enrich_tracks(self, *_, **__) -> None:
        """
        Call API to enrich elements of track objects improving metadata coverage.
        This is an optionally implementable method. Defaults to doing nothing.
        """
        self.logger.debug("Enrich tracks not implemented for this library, skipping...")

    def log_tracks(self) -> None:
        playlist_tracks = [track.uri for tracks in self.playlists.values() for track in tracks]
        in_playlists = len([track for track in self.tracks if track.uri in playlist_tracks])
        album_tracks = [track.uri for tracks in self.albums for track in tracks]
        in_albums = len([track for track in self.tracks if track.uri in album_tracks])

        width = get_max_width(self.playlists)
        self.logger.stat(
            f"\33[1;96m{"USER'S " + self.api.source.upper() + " TRACKS":<{width}}\33[1;0m |"
            f"\33[92m{in_playlists:>7} in playlists  \33[0m|"
            f"\33[92m{in_albums:>7} in saved albums \33[0m|"
            f"\33[1;94m{len(self.tracks):>7} total tracks \33[0m"
        )

    ###########################################################################
    ## Load - albums
    ###########################################################################
    def load_saved_albums(self) -> None:
        """
        Load all user's saved albums from the API.
        Updates currently loaded albums in-place or appends if not already loaded.
        """
        self.logger.debug(f"Load user's saved {self.api.source} albums: START")
        self.api.load_user_data()

        responses = self.api.get_user_items(kind=RemoteObjectType.ALBUM, use_cache=self.use_cache)
        for response in self.logger.get_progress_bar(iterable=responses, desc="Processing albums", unit="albums"):
            album = self.factory.album(response=response, skip_checks=True)

            current = next((item for item in self._albums if item == album), None)
            if current is None:
                self._albums.append(album)
            else:
                current._response = album.response
                current.refresh(skip_checks=True)

            for track in album.tracks:  # add tracks from this album to the user's saved tracks
                if track not in self.tracks:
                    self._tracks.append(track)

        self.logger.debug(f"Load user's saved {self.api.source} albums: DONE")

    def enrich_saved_albums(self, *_, **__) -> None:
        """
        Call API to enrich elements of user's saved album objects improving metadata coverage.
        This is an optionally implementable method. Defaults to doing nothing.
        """
        self.logger.debug("Enrich albums not implemented for this library, skipping...")

    def log_albums(self) -> None:
        """Log stats on currently loaded albums"""
        width = get_max_width(self.playlists)
        self.logger.stat(
            f"\33[1;96m{"USER'S " + self.api.source.upper() + " ALBUMS":<{width}}\33[1;0m |"
            f"\33[92m{sum(len(album.tracks) for album in self.albums):>7} album tracks  \33[0m|"
            f"\33[92m{sum(len(album.artists) for album in self.albums):>7} album artists   \33[0m|"
            f"\33[1;94m{len(self.artists):>7} total albums \33[0m"
        )

    ###########################################################################
    ## Load - artists
    ###########################################################################
    def load_saved_artists(self) -> None:
        """
        Load all user's saved artists from the API.
        Updates currently loaded artists in-place or appends if not already loaded.
        """
        self.logger.debug(f"Load user's saved {self.api.source} artists: START")
        self.api.load_user_data()

        responses = self.api.get_user_items(kind=RemoteObjectType.ARTIST, use_cache=self.use_cache)
        for response in self.logger.get_progress_bar(iterable=responses, desc="Processing artists", unit="artists"):
            artist = self.factory.artist(response=response, skip_checks=True)

            current = next((item for item in self._artists if item == artist), None)
            if current is None:
                self._artists.append(artist)
            else:
                current._response = artist.response
                current.refresh(skip_checks=True)

        self.logger.debug(f"Load user's saved {self.api.source} artists: DONE")

    def enrich_saved_artists(self, *_, **__) -> None:
        """
        Call API to enrich elements of user's saved artist objects improving metadata coverage.
        This is an optionally implementable method. Defaults to doing nothing.
        """
        self.logger.debug("Enrich artists not implemented for this library, skipping...")

    def log_artists(self) -> None:
        """Log stats on currently loaded artists"""
        width = get_max_width(self.playlists)
        self.logger.stat(
            f"\33[1;96m{"USER'S " + self.api.source.upper() + " ARTISTS":<{width}}\33[1;0m |"
            f"\33[92m{sum(len(artist.tracks) for artist in self.artists):>7} artist tracks \33[0m|"
            f"\33[92m{sum(len(artist.albums) for artist in self.artists):>7} artist albums   \33[0m|"
            f"\33[1;94m{len(self.artists):>7} total artists \33[0m"
        )

    ###########################################################################
    ## Backup/Restore/Sync
    ###########################################################################
    def backup_playlists(self) -> dict[str, list[str]]:
        """
        Produce a backup map of <playlist name>: [<URIs] for all playlists in this library
        which can be saved to JSON for backup purposes.
        """
        return {name: [track.uri for track in pl] for name, pl in self.playlists.items()}

    def restore_playlists(
            self,
            playlists: Library | Collection[Playlist] | Mapping[str, Iterable[Track]] | Mapping[str, Iterable[str]],
            dry_run: bool = True,
    ) -> None:
        """
        Restore playlists from a backup to loaded playlist objects.

        This function does not sync the updated playlists with the remote library.

        When ``dry_run`` is False, this function does create new playlists on the remote library for playlists
        given that do not exist in this Library.

        :param playlists: Values that represent the playlists to restore from.
        :param dry_run: When True, do not create playlists
            and just skip any playlists that are not already currently loaded.
        """
        if isinstance(playlists, Library):  # get URIs from playlists in library
            playlists = {name: [track.uri for track in pl] for name, pl in playlists.playlists.items()}
        elif (
                isinstance(playlists, Mapping)
                and all(isinstance(v, MusifyItem) for vals in playlists.values() for v in vals)
        ):
            # get URIs from playlists in map values
            playlists = {name: [item.uri for item in pl] for name, pl in playlists.items()}
        elif not isinstance(playlists, Mapping) and isinstance(playlists, Collection):
            # get URIs from playlists in collection
            playlists = {pl.name: [track.uri for track in pl] for pl in playlists}
        playlists: Mapping[str, Iterable[str]]

        uri_tracks = {track.uri: track for track in self.tracks}
        uri_get = [uri for uri_list in playlists.values() for uri in uri_list if uri not in uri_tracks]

        if uri_get:
            tracks_data = self.api.get_tracks(uri_get, features=False, use_cache=self.use_cache)
            tracks = list(map(self.factory.track, tracks_data))
            uri_tracks |= {track.uri: track for track in tracks}

        for name, uri_list in playlists.items():
            playlist = self.playlists.get(name)
            if not playlist and dry_run:  # skip on dry run
                continue
            if not playlist:  # new playlist given, create it on remote first
                # noinspection PyArgumentList
                playlist = self.factory.playlist.create(name=name)

            playlist._tracks = [uri_tracks.get(uri) for uri in uri_list]
            self.playlists[name] = playlist

    def sync(
            self,
            playlists: Library | Mapping[str, Iterable[MusifyItem]] | Collection[Playlist] | None = None,
            kind: Literal["new", "refresh", "sync"] = "new",
            reload: bool = True,
            dry_run: bool = True
    ) -> dict[str, SyncResultRemotePlaylist]:
        """
        Synchronise this playlist object with the remote playlist it is associated with.

        Clear options:
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
        self.logger.debug(f"Sync {self.api.source} playlists: START")

        if not playlists:  # use the playlists as stored in this library object
            playlists = self.playlists
        elif isinstance(playlists, Library):  # get map of playlists from the given library
            playlists = playlists.playlists
        elif isinstance(playlists, Collection) and all(isinstance(pl, Playlist) for pl in playlists):
            # reformat list to map
            playlists = {pl.name: pl for pl in playlists}
        playlists: Mapping[str, Iterable[MusifyItem]]

        log_kind = "adding new items only"
        if kind != "new":
            log_kind = 'all' if kind == 'refresh' else 'extra'
            log_kind = f"clearing {log_kind} items from {self.api.source} playlist first"
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Synchronising {len(playlists)} {self.api.source} playlists: {log_kind}"
            f"{f' and reloading stored playlists' if reload else ''} \33[0m"
        )

        bar = self.logger.get_progress_bar(
            iterable=playlists.items(), desc=f"Synchronising {self.api.source}", unit="playlists"
        )
        results = {}
        for name, pl in bar:  # synchronise playlists
            if name not in self.playlists:  # new playlist given, create it on remote first
                if dry_run:
                    results[name] = SyncResultRemotePlaylist(
                        start=0, added=len(pl), removed=0, unchanged=0, difference=len(pl), final=len(pl)
                    )
                    continue

                # noinspection PyArgumentList
                self.playlists[name] = self.factory.playlist.create(name=name)
            results[name] = self.playlists[name].sync(items=pl, kind=kind, reload=reload, dry_run=dry_run)

        self.logger.print()
        self.logger.debug(f"Sync {self.api.source} playlists: DONE\n")
        return results

    def log_sync(self, results: SyncResultRemotePlaylist | Mapping[str, SyncResultRemotePlaylist]) -> None:
        """Log stats from the results of a ``sync`` operation"""
        if not results:
            return
        if not isinstance(results, Mapping):
            results = {"": results}

        max_width = get_max_width(results)

        self.logger.stat(f"\33[1;96mSync {self.api.source} playlists' stats: \33[0m")
        for name, result in results.items():
            self.logger.stat(
                f"\33[97m{align_string(name, max_width=max_width)} \33[0m|"
                f"\33[96m{result.start:>6} initial \33[0m|"
                f"\33[92m{result.added:>6} added \33[0m|"
                f"\33[91m{result.removed:>6} removed \33[0m|"
                f"\33[93m{result.unchanged:>6} unchanged \33[0m|"
                f"\33[94m{result.difference:>6} difference \33[0m|"
                f"\33[1;97m{result.final:>6} final \33[0m"
            )
