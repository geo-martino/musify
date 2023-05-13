from typing import Optional, List, MutableMapping, Any

from syncify.abstract.collection import ItemCollection
from syncify.spotify import ItemType
from syncify.spotify.api import API
from syncify.spotify.library.item import SpotifyResponse, SpotifyTrack
from syncify.spotify.library.playlist import SpotifyPlaylist
from syncify.utils.logger import Logger


class SpotifyLibrary(Logger, ItemCollection):
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

    def __init__(
            self,
            api: API,
            include: Optional[List[str]] = None,
            exclude: Optional[List[str]] = None,
            use_cache: bool = True
    ):
        Logger.__init__(self)
        self._logger.debug("Load Spotify library: START")

        self._api = api
        self.include = include
        self.exclude = exclude
        self.use_cache = use_cache
        SpotifyResponse.api = api

        self._logger.info(f"\33[1;95m ->\33[1;97m Loading Spotify library \33[0m")
        self._line()

        playlists_data = self._get_playlists_data()
        self._line()
        tracks_data = self._get_tracks_data(playlists_data=playlists_data)
        self._line()

        self._logger.info(f"\33[1;95m  >\33[1;97m Processing Spotify library of "
                          f"{len(tracks_data)} tracks and {len(playlists_data)} playlists \33[0m")

        self.tracks = [SpotifyTrack(track) for track in tracks_data]
        playlists = [SpotifyPlaylist.load(pl, items=self.tracks, use_cache=use_cache) for pl in playlists_data]
        self.playlists = {pl.name: pl for pl in sorted(playlists, key=lambda pl: pl.name.casefold())}
        self._line()
        self.log_tracks()
        self.log_playlists()
        self._line()

        self._logger.debug("Load Spotify library: DONE\n")

    def _get_tracks_data(self, playlists_data: List[MutableMapping[str, Any]]) -> List[MutableMapping[str, Any]]:
        """Get a list of unique tracks with enhanced data (i.e. features, genres etc.) across all playlists"""
        self._logger.debug("Load Spotify tracks data: START")
        playlists_tracks_data = [pl["tracks"]["items"] for pl in playlists_data]

        tracks_data = []
        tracks_seen = set()
        for track in [item["track"] for pl in playlists_tracks_data for item in pl]:
            if not track["is_local"] and track["uri"] not in tracks_seen:
                tracks_seen.add(track["uri"])
                tracks_data.append(track)

        self._logger.info(f"\33[1;95m  >\33[1;97m Getting Spotify data for {len(tracks_data)} unique tracks \33[0m")
        self.api.get_items(tracks_data, kind=ItemType.TRACK, limit=50, use_cache=self.use_cache)
        self.api.get_tracks_extra(tracks_data, features=True, limit=50, use_cache=self.use_cache)

        self._logger.debug("Load Spotify tracks data: DONE\n")
        return tracks_data

    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        playlist_tracks = [track.uri for tracks in self.playlists.values() for track in tracks]
        in_playlists = len([track for track in self.tracks if track.uri in playlist_tracks])

        self._logger.info(f"\33[1;96m{'SPOTIFY TRACKS':<22}\33[1;0m|"
                          f"\33[92m{in_playlists:>6} in playlists \33[0m|"
                          f"\33[1m{len(self.tracks):>6} total \33[0m")

    def _get_playlists_data(self) -> List[MutableMapping[str, Any]]:
        """Get playlists and all their tracks"""
        self._logger.debug("Get Spotify playlists data: START")
        playlists_data = self.api.get_collections_user(kind=ItemType.PLAYLIST, limit=self.limit,
                                                       use_cache=self.use_cache)
        playlists_total = len(playlists_data)
        if self.include:
            include = [name.lower() for name in self.include]
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() in include]

        if self.exclude:
            exclude = [name.lower() for name in self.exclude]
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() not in exclude]

        self._logger.debug(f"Filtered out {playlists_total - len(playlists_data)} playlists "
                           f"from {playlists_total} Spotify playlists")

        total_tracks = sum(pl["tracks"]["total"] for pl in playlists_data)
        total_pl = len(playlists_data)
        self._logger.info(f"\33[1;95m  >\33[1;97m "
                          f"Getting {total_tracks} Spotify tracks from {total_pl} playlists \33[0m")

        self.api.get_collections(playlists_data, kind=ItemType.PLAYLIST, limit=self.limit, use_cache=self.use_cache)

        self._logger.debug("Get Spotify playlists data: DONE\n")
        return playlists_data

    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        max_width = self._get_max_width(self.playlists)

        self._logger.info("\33[1;96mLoaded the following Spotify playlists: \33[0m")
        for name, playlist in self.playlists.items():
            name = self._truncate_align_str(playlist.name, max_width=max_width)
            self._logger.info(f"{name} | \33[92m{len(playlist):>6} total tracks \33[0m")

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "user_name": self.api.user_name,
            "user_id": self.api.user_id,
            "track_count": len(self.tracks),
            "playlist_counts": {name: len(pl) for name, pl in self.playlists},
        }
