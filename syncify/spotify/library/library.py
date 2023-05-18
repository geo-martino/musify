from typing import Optional, List, MutableMapping, Any, Collection, Union, Mapping, Literal

from syncify.abstract import Item
from syncify.abstract.collection import Library, ItemCollection, Playlist
from syncify.spotify import ItemType
from syncify.spotify.api import API
from syncify.spotify.library.item import SpotifyResponse, SpotifyTrack
from syncify.spotify.library.playlist import SpotifyPlaylist
from syncify.utils.logger import Logger


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
    def api(self) -> API:
        return self._api

    @property
    def name(self) -> Optional[str]:
        return self.api.user_name

    @property
    def items(self) -> List[SpotifyTrack]:
        return self.tracks

    @property
    def playlists(self) -> MutableMapping[str, SpotifyPlaylist]:
        return self._playlists

    def __init__(
            self,
            api: API,
            include: Optional[List[str]] = None,
            exclude: Optional[List[str]] = None,
            use_cache: bool = True,
            load: bool = True,
    ):
        Logger.__init__(self)

        self._api = api
        self.include = include
        self.exclude = exclude
        self.use_cache = use_cache
        SpotifyResponse.api = api

        self.tracks: List[SpotifyTrack] = []
        self._playlists: MutableMapping[str, SpotifyPlaylist] = {}

        if load:
            self.load()

    def load(self, log: bool = True):
        self.logger.debug("Load Spotify library: START")
        self.logger.info(f"\33[1;95m ->\33[1;97m Loading Spotify library \33[0m")
        self.print_line()

        playlists_data = self._get_playlists_data()
        self.print_line()
        tracks_data = self._get_tracks_data(playlists_data=playlists_data)
        self.print_line()

        self.logger.info(f"\33[1;95m  >\33[1;97m Processing Spotify library of "
                         f"{len(tracks_data)} tracks and {len(playlists_data)} playlists \33[0m")

        self.tracks = [SpotifyTrack(track) for track in tracks_data]
        playlists = [SpotifyPlaylist.load(pl, items=self.tracks, use_cache=self.use_cache) for pl in playlists_data]
        self._playlists = {pl.name: pl for pl in sorted(playlists, key=lambda pl: pl.name.casefold())}
        self.print_line()

        if log:
            self.log_playlists()
            self.print_line()
            self.log_tracks()
            self.print_line()

        self.logger.debug("Load Spotify library: DONE\n")

    def _get_tracks_data(self, playlists_data: List[MutableMapping[str, Any]]) -> List[MutableMapping[str, Any]]:
        """Get a list of unique tracks with enhanced data (i.e. features, genres etc.) across all playlists"""
        self.logger.debug("Load Spotify tracks data: START")
        playlists_tracks_data = [pl["tracks"]["items"] for pl in playlists_data]

        tracks_data = []
        tracks_seen = set()
        for track in [item["track"] for pl in playlists_tracks_data for item in pl]:
            if not track["is_local"] and track["uri"] not in tracks_seen:
                tracks_seen.add(track["uri"])
                tracks_data.append(track)

        self.logger.info(f"\33[1;95m  >\33[1;97m Getting Spotify data for {len(tracks_data)} unique tracks "
                         f"across {len(playlists_data)} playlists \33[0m")
        self.api.get_items(tracks_data, kind=ItemType.TRACK, limit=50, use_cache=self.use_cache)
        self.api.get_tracks_extra(tracks_data, features=True, limit=50, use_cache=self.use_cache)

        self.logger.debug("Load Spotify tracks data: DONE\n")
        return tracks_data

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        playlist_tracks = [track.uri for tracks in self.playlists.values() for track in tracks]
        in_playlists = len([track for track in self.tracks if track.uri in playlist_tracks])

        self.logger.info(f"\33[1;96m{'SPOTIFY TOTALS':<22}\33[1;0m|"
                         f"\33[92m{in_playlists:>6} in playlists \33[0m|"
                         f"\33[97m{len(self.tracks):>6} total \33[0m")

    def _get_playlists_data(self) -> List[MutableMapping[str, Any]]:
        """Get playlists and all their tracks"""
        self.logger.debug("Get Spotify playlists data: START")
        playlists_data = self.api.get_collections_user(kind=ItemType.PLAYLIST, limit=self.limit,
                                                       use_cache=self.use_cache)
        playlists_total = len(playlists_data)
        if self.include:
            include = [name.lower() for name in self.include]
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() in include]

        if self.exclude:
            exclude = [name.lower() for name in self.exclude]
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() not in exclude]

        self.logger.debug(f"Filtered out {playlists_total - len(playlists_data)} playlists "
                          f"from {playlists_total} Spotify playlists")

        total_tracks = sum(pl["tracks"]["total"] for pl in playlists_data)
        total_pl = len(playlists_data)
        self.logger.info(f"\33[1;95m  >\33[1;97m "
                         f"Getting {total_tracks} Spotify tracks from {total_pl} playlists \33[0m")

        self.api.get_collections(playlists_data, kind=ItemType.PLAYLIST, limit=self.limit, use_cache=self.use_cache)

        self.logger.debug("Get Spotify playlists data: DONE\n")
        return playlists_data

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = self.get_max_width(self.playlists)

        self.logger.info("\33[1;96mLoaded the following Spotify playlists: \33[0m")
        for name, playlist in self.playlists.items():
            name = self.truncate_align_str(playlist.name, max_width=max_width)
            self.logger.info(f"\33[97m{name} \33[0m| \33[92m{len(playlist):>6} total tracks \33[0m")

    def sync(self,
             playlists: Optional[Union[Library, Mapping[str, Playlist], List[Playlist]]] = None,
             clear: Optional[Literal['all', 'extra']] = None,
             reload: bool = True):
        self.logger.debug("Update Spotify: START")
        count = len(playlists if playlists else self.playlists)
        clearing = f", clearing {clear} tracks" if clear else ""
        reloading = " and reloading Syncify" if reload else ""
        self.logger.info(f"\33[1;95m ->\33[1;97m Synchronising {count} Spotify playlists{clearing}{reloading} \33[0m")

        if not playlists:
            playlists = self.playlists
        elif isinstance(playlists, list):
            playlists = {pl.name: pl for pl in playlists}
        elif isinstance(playlists, Library):
            playlists = playlists.playlists
        playlists: Mapping[str, Playlist]

        bar = self.get_progress_bar(iterable=playlists.items(), desc="Synchronising Spotify", unit="playlists")
        for name, playlist in bar:
            spotify = self.playlists.get(name)
            if not spotify:
                spotify = SpotifyPlaylist.create(name=name)
            spotify.sync(items=playlist, clear=clear, reload=reload)

        self.logger.debug("Update Spotify: DONE\n")
        self.print_line()

    def restore_playlists(self, backup: str, in_playlists: list = None, ex_playlists: list = None, **kwargs) -> dict:
        """
        Restore Spotify playlists from backup.

        :param backup: str. Filename of backup json in form <name>: <list of dicts of track's metadata>
        :param in_playlists: list, default=None. Only restore playlists in this list.
        :param ex_playlists: list, default=None. Don't restore playlists in this list.
        """
        self.logger.info(f"\33[1;95m -> \33[1;97mRestoring Spotify playlists from backup file: {backup} \33[0m")

        backup = self.load_json(backup, parent=True, **kwargs)
        if not backup:
            self.logger.info(f"\33[91mBackup file not found.\33[0m")
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

        # set clear kwarg to all
        kwargs_mod = kwargs.copy()
        kwargs_mod['clear'] = 'all'

        self.update_playlists(backup, **kwargs_mod)

        self.logger.info(f"\33[92mRestored {len(backup)} Spotify playlists \33[0m")

    def extend(self, items: Union[ItemCollection, Collection[Item]]) -> None:
        self.logger.debug("Extend Spotify tracks data: START")
        load_uris = []
        for track in items:
            if track in self.tracks:
                continue
            elif isinstance(track, SpotifyTrack):
                self.tracks.append(track)
            elif track.has_uri:
                load_uris.append(track.uri)

        if not load_uris:
            return

        self.logger.info(f"\33[1;95m  >\33[1;97m "
                         f"Extending Spotify library with {len(load_uris)} additional tracks \33[0m")
        load_tracks = self.api.get_items(load_uris, kind=ItemType.TRACK, limit=50, use_cache=self.use_cache)
        self.api.get_tracks_extra(load_tracks, features=True, limit=50, use_cache=self.use_cache)
        self.tracks.extend(SpotifyTrack(response) for response in load_tracks)
        self.print_line()
        self.log_tracks()
        self.print_line()

        self.logger.debug("Extend Spotify tracks data: DONE\n")

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "user_name": self.api.user_name,
            "user_id": self.api.user_id,
            "track_count": len(self.tracks),
            "playlist_counts": {name: len(pl) for name, pl in self.playlists.items()},
        }
