from collections.abc import Collection, Mapping, Iterable
from typing import Any, Literal

from syncify.abstract.collection import Library, Playlist
from syncify.abstract.item import Item
from syncify.spotify.api.api import API
from syncify.spotify.base import SpotifyObject
from syncify.spotify.enums import ItemType
from syncify.spotify.library.item import SpotifyTrack
from syncify.spotify.library.playlist import SpotifyPlaylist, SyncResultSpotifyPlaylist
from syncify.utils.logger import Logger, REPORT, STAT


class SpotifyLibrary(Library):
    """
    Represents a Spotify library, providing various methods for manipulating
    tracks and playlists across an entire Spotify library collection.

    :param api: An authorised API object for the authenticated user you wish to load the library from.
    :param include: An optional list of playlist names to include when loading playlists.
    :param exclude: An optional list of playlist names to exclude when loading playlists.
    :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
    """
    limit = 50

    @property
    def name(self):
        """The user ID associated with this library"""
        return self.api.user_id

    @property
    def items(self) -> list[SpotifyTrack]:
        return self.tracks

    @property
    def tracks(self) -> list[SpotifyTrack]:
        return self._tracks

    @property
    def playlists(self) -> dict[str, SpotifyPlaylist]:
        return self._playlists

    @property
    def api(self) -> API:
        """Authorised API object for making authenticated calls to a user's library"""
        return self._api

    def __init__(
            self,
            api: API,
            include: Iterable[str] | None = None,
            exclude: Iterable[str] | None = None,
            use_cache: bool = True,
            load: bool = True,
    ):
        Logger.__init__(self)

        self._api = api
        self.include = include
        self.exclude = exclude
        self.use_cache = use_cache
        SpotifyObject.api = api

        self._tracks: list[SpotifyTrack] = []
        self._playlists: dict[str, SpotifyPlaylist] = {}

        if load:
            self.load()

    def load(self, log: bool = True) -> None:
        """Loads all tracks and playlists in this library from scratch and log results."""
        self.logger.debug("Load Spotify library: START")

        self.logger.info(f"\33[1;95m ->\33[1;97m Loading Spotify library \33[0m")
        self.print_line()

        # get raw API responses
        playlists_data = self._get_playlists_data()
        tracks_data = self._get_tracks_data(playlists_data=playlists_data)

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Processing Spotify library of "
            f"{len(tracks_data)} tracks and {len(playlists_data)} playlists \33[0m"
        )
        track_bar = self.get_progress_bar(iterable=tracks_data, desc="Processing tracks", unit="tracks")
        playlists_bar = self.get_progress_bar(iterable=playlists_data, desc="Processing playlists", unit="playlists")

        # process to Spotify objects
        self._tracks = list(map(SpotifyTrack, track_bar))
        playlists = [SpotifyPlaylist.load(pl, items=self.tracks, use_cache=self.use_cache) for pl in playlists_bar]
        self._playlists = {pl.name: pl for pl in sorted(playlists, key=lambda pl: pl.name.casefold())}

        self.print_line()
        if log:
            self.log_playlists()
            self.log_tracks()

        self.logger.debug("Load Spotify library: DONE\n")

    def _get_tracks_data(self, playlists_data: Collection[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Get a list of unique tracks with enhanced data (i.e. features, genres etc.) across all playlists"""
        self.logger.debug("Load Spotify tracks data: START")
        playlists_tracks_data = [pl["tracks"]["items"] for pl in playlists_data]

        tracks_data: list[dict[str, Any]] = []
        tracks_seen = set()
        for track in [item["track"] for pl in playlists_tracks_data for item in pl]:
            if not track["is_local"] and track["uri"] not in tracks_seen:
                tracks_seen.add(track["uri"])
                tracks_data.append(track)

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Getting Spotify data for {len(tracks_data)} unique tracks "
            f"across {len(playlists_data)} playlists \33[0m"
        )
        self.api.get_tracks(tracks_data, features=True, use_cache=self.use_cache)

        self.print_line()
        self.logger.debug("Load Spotify tracks data: DONE\n")
        return tracks_data

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        playlist_tracks = [track.uri for tracks in self.playlists.values() for track in tracks]
        in_playlists = len([track for track in self.tracks if track.uri in playlist_tracks])

        width = self.get_max_width(self.playlists)
        self.logger.report(
            f"\33[1;96m{'SPOTIFY ITEMS':<{width}}\33[1;0m |"
            f"\33[92m{in_playlists:>7} in playlists \33[0m|"
            f"\33[1;94m{len(self.tracks):>6} total \33[0m"
        )
        self.print_line(REPORT)

    def enrich_tracks(self, albums: bool = False, artists: bool = False) -> None:
        """Call API to enrich elements of track objects improving metadata coverage"""
        if not albums and not artists:
            return
        self.logger.debug("Enrich Spotify library: START")

        self.logger.info(f"\33[1;95m  >\33[1;97m Enriching metadata for {len(self.tracks)} Spotify tracks \33[0m")

        if albums:  # enrich track albums
            album_uris: set[str] = {track.response["album"]["uri"] for track in self.tracks}
            album_responses = self.api.get_items(
                album_uris, kind=ItemType.ALBUM, limit=20, use_cache=self.use_cache
            )

            albums = {response["uri"]: response for response in album_responses}
            for track in self.tracks:
                track.response["album"] = albums[track.response["album"]["uri"]]

        if artists:  # enrich track artists
            artist_uris: set[str] = {artist["uri"] for track in self.tracks for artist in track.response["artists"]}
            artist_responses = self.api.get_items(
                artist_uris, kind=ItemType.ARTIST, limit=20, use_cache=self.use_cache
            )

            artists = {response["uri"]: response for response in artist_responses}
            for track in self.tracks:
                track.response["artists"] = [artists[artist["uri"]] for artist in track.response["artists"]]

        self.print_line()
        self.logger.debug("Enrich Spotify library: DONE\n")

    def _get_playlists_data(self) -> list[dict[str, Any]]:
        """Get playlists and all their tracks"""
        self.logger.debug("Get Spotify playlists data: START")
        playlists_data = self.api.get_collections_user(
            kind=ItemType.PLAYLIST, limit=self.limit, use_cache=self.use_cache
        )
        playlists_total = len(playlists_data)
        if self.include:  # filter on include playlist names
            include = {name.lower() for name in self.include}
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() in include]

        if self.exclude:  # filter out exclude playlist names
            exclude = {name.lower() for name in self.exclude}
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() not in exclude]

        self.logger.debug(
            f"Filtered out {playlists_total - len(playlists_data)} playlists "
            f"from {playlists_total} Spotify playlists"
        )

        total_tracks = sum(pl["tracks"]["total"] for pl in playlists_data)
        total_pl = len(playlists_data)
        self.logger.info(
            f"\33[1;95m  >\33[1;97m Getting {total_tracks} Spotify tracks from {total_pl} playlists \33[0m"
        )

        # make API calls
        self.api.get_collections(playlists_data, kind=ItemType.PLAYLIST, limit=self.limit, use_cache=self.use_cache)

        self.print_line()
        self.logger.debug("Get Spotify playlists data: DONE\n")
        return playlists_data

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = self.get_max_width(self.playlists)

        self.logger.report("\33[1;96mLoaded the following Spotify playlists: \33[0m")
        for name, playlist in self.playlists.items():
            name = self.align_and_truncate(playlist.name, max_width=max_width)
            self.logger.report(f"\33[97m{name} \33[0m| \33[92m{len(playlist):>6} total tracks \33[0m")
        self.print_line(REPORT)

    def sync(
            self,
            playlists: Library | Mapping[str, Playlist] | Collection[Playlist] | None = None,
            clear: Literal["all", "extra"] | None = None,
            reload: bool = True,
            dry_run: bool = True
    ) -> dict[str, SyncResultSpotifyPlaylist]:
        """
        Synchronise this playlist object with the remote Spotify playlist it is associated with. Clear options:

        * None: Do not clear any items from the remote playlist and only add any tracks
            from this playlist object not currently in the remote playlist.
        * 'all': Clear all items from the remote playlist first, then add all items from this playlist object.
        * 'extra': Clear all items not currently in this object's items list, then add all tracks
            from this playlist object not currently in the remote playlist.

        :param playlists: Provide a library, map of playlist name to playlist or collection of playlists
            to synchronise to the remote Spotify library.
            Use the currently loaded ``playlists`` in this object if not given.
        :param clear: Clear option for the remote playlist. See description.
        :param reload: When True, once synchronisation is complete, reload this SpotifyPlaylist object
            to reflect the changes on the remote playlist if enabled. Skip if False.
        :param dry_run: Run function, but do not modify the remote playlists at all.
        :return: Map of playlist name to UpdateResult object with stats on the changes to each remote playlist.
        """
        self.logger.debug("Update Spotify: START")

        count = len(playlists if playlists else self.playlists)
        clearing = f", clearing {clear} tracks" if clear else ""
        reloading = " and reloading Syncify" if reload else ""
        self.logger.info(f"\33[1;95m ->\33[1;97m Synchronising {count} Spotify playlists{clearing}{reloading} \33[0m")

        if not playlists:  # use the playlists as stored in this library object
            playlists = self.playlists
        elif isinstance(playlists, Collection):  # reformat list to map
            playlists = {pl.name: pl for pl in playlists}
        elif isinstance(playlists, Library):  # get map of playlists from the given library
            playlists = playlists.playlists
        playlists: Mapping[str, Playlist]

        bar = self.get_progress_bar(iterable=playlists.items(), desc="Synchronising Spotify", unit="playlists")
        results = {}
        for name, playlist in bar:  # synchronise playlists
            spotify = self.playlists.get(name)
            if not spotify:  # new playlist given, create it on remote first
                spotify = SpotifyPlaylist.create(name=name)
            results[name] = spotify.sync(items=playlist, clear=clear, reload=reload, dry_run=dry_run)

        self.print_line()
        self.logger.debug("Update Spotify: DONE\n")
        return results

    def log_sync(self, results: Mapping[str, SyncResultSpotifyPlaylist]) -> None:
        """Log stats from the results of a ``sync`` operation"""
        if not results:
            return

        max_width = self.get_max_width(self.playlists)

        self.logger.stat("\33[1;96mSync Spotify playlists' stats: \33[0m")
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

    def extend(self, items: Iterable[Item]) -> None:
        self.logger.debug("Extend Spotify tracks data: START")
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Extending library: checking if the given items are already in this library \33[0m"
        )

        load_uris = []
        for track in items:
            if track in self.tracks:
                continue
            elif isinstance(track, SpotifyTrack):
                self.tracks.append(track)
            elif track.has_uri:
                load_uris.append(track.uri)

        self.print_line()
        if not load_uris:
            return

        self.logger.info(
            f"\33[1;95m  >\33[1;97m Extending Spotify library with {len(load_uris)} additional tracks \33[0m"
        )

        load_tracks = self.api.get_tracks(load_uris, features=True, use_cache=self.use_cache)
        self.tracks.extend(SpotifyTrack(response) for response in load_tracks)

        self.print_line()
        self.log_tracks()
        self.logger.debug("Extend Spotify tracks data: DONE\n")

    def merge_playlists(self, playlists: Library | Collection[Playlist] | Mapping[Any, Playlist] | None = None):
        raise NotImplementedError

    def restore_playlists(self, backup: Mapping[str, Iterable[str]]) -> None:
        """
        Restore playlists from a backup to loaded playlist objects.
        This does not sync the updated playlists with Spotify.
        """
        uri_tracks = {track.uri: track for track in self.tracks}

        uris = [uri for uri_list in backup.values() for uri in uri_list if uri not in uri_tracks]
        if uris:
            tracks_data = self.api.get_tracks(uris, features=True, use_cache=self.use_cache)
            tracks = list(map(SpotifyTrack, tracks_data))
            uri_tracks |= {track.uri: track for track in tracks}

        for name, uris in backup.items():
            tracks = [uri_tracks.get(uri) for uri in uris]
            playlist = SpotifyPlaylist.create(name) if name not in self.playlists else self.playlists[name]
            playlist._tracks = tracks
            self.playlists[name] = playlist

    def as_dict(self):
        return {
            "user_name": self.api.user_name,
            "user_id": self.api.user_id,
            "track_count": len(self.tracks),
            "playlist_counts": {name: len(pl) for name, pl in self.playlists.items()},
        }

    def as_json(self):
        return {
            "user_name": self.api.user_name,
            "user_id": self.api.user_id,
            "tracks": dict(sorted(((track.uri, track.as_json()) for track in self.tracks), key=lambda x: x[0])),
            "playlists": {name: [tr.uri for tr in pl] for name, pl in self.playlists.items()},
        }
