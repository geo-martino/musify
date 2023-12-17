from collections.abc import Collection, Mapping
from typing import Any

from syncify.abstract.collection import Playlist, Library
from syncify.remote.enums import RemoteItemType
from syncify.remote.library.library import RemoteLibrary
from syncify.remote.types import RemoteObjectClasses
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from .collection import SpotifyAlbum
from .item import SpotifyTrack
from .playlist import SpotifyPlaylist


class SpotifyLibrary(RemoteLibrary[SpotifyTrack], SpotifyDataWrangler):
    """
    Represents a Spotify library, providing various methods for manipulating
    tracks and playlists across an entire Spotify library collection.
    """
    
    @property
    def _remote_types(self) -> RemoteObjectClasses:
        return RemoteObjectClasses(
            track=SpotifyTrack, album=SpotifyAlbum, playlist=SpotifyPlaylist
        )

    def _get_tracks_data(self, playlists_data: Collection[Mapping[str, Any]]) -> list[dict[str, Any]]:
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

    def enrich_tracks(self, albums: bool = False, artists: bool = False) -> None:
        if not albums and not artists:
            return
        self.logger.debug("Enrich Spotify library: START")

        self.logger.info(f"\33[1;95m  >\33[1;97m Enriching metadata for {len(self.tracks)} Spotify tracks \33[0m")

        if albums:  # enrich track albums
            album_uris: set[str] = {track.response["album"]["uri"] for track in self.tracks}
            album_responses = self.api.get_items(
                album_uris, kind=RemoteItemType.ALBUM, limit=20, use_cache=self.use_cache
            )

            albums = {response["uri"]: response for response in album_responses}
            for track in self.tracks:
                track.response["album"] = albums[track.response["album"]["uri"]]

        if artists:  # enrich track artists
            artist_uris: set[str] = {artist["uri"] for track in self.tracks for artist in track.response["artists"]}
            artist_responses = self.api.get_items(
                artist_uris, kind=RemoteItemType.ARTIST, limit=20, use_cache=self.use_cache
            )

            artists = {response["uri"]: response for response in artist_responses}
            for track in self.tracks:
                track.response["artists"] = [artists[artist["uri"]] for artist in track.response["artists"]]

        self.print_line()
        self.logger.debug("Enrich Spotify library: DONE\n")

    def _get_playlists_data(self) -> list[dict[str, Any]]:
        self.logger.debug("Get Spotify playlists data: START")
        playlists_data = self.api.get_user_items(
            kind=RemoteItemType.PLAYLIST, limit=self.limit, use_cache=self.use_cache
        )
        playlists_total = len(playlists_data)
        if self.include:  # filter on include playlist names
            include = {name.casefold() for name in self.include}
            playlists_data = [pl for pl in playlists_data if pl["name"].casefold() in include]

        if self.exclude:  # filter out exclude playlist names
            exclude = {name.casefold() for name in self.exclude}
            playlists_data = [pl for pl in playlists_data if pl["name"].casefold() not in exclude]

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
        self.api.get_items(playlists_data, kind=RemoteItemType.PLAYLIST, use_cache=self.use_cache)

        self.print_line()
        self.logger.debug("Get Spotify playlists data: DONE\n")
        return playlists_data

    def merge_playlists(
            self, playlists: Library | Collection[Playlist] | Mapping[Any, Playlist] | None = None
    ) -> None:
        raise NotImplementedError
