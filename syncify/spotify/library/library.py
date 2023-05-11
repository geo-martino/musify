from typing import Optional, List, MutableMapping, Any

from local.library import LocalLibrary, MusicBee
import json
import os

from syncify.spotify import __URL_AUTH__, __URL_API__, ItemType
from syncify.spotify.api import API
from syncify.spotify.library.playlist import SpotifyPlaylist
from syncify.spotify.library.item import SpotifyResponse, SpotifyTrack
from syncify.utils.logger import Logger


class SpotifyLibrary(Logger):
    limit = 50

    def __init__(
            self,
            api: API,
            include_playlists: Optional[List[str]] = None,
            exclude_playlists: Optional[List[str]] = None,
            use_cache: bool = True
    ):
        Logger.__init__(self)
        self.api = api
        self.include_playlists = include_playlists
        self.exclude_playlists = exclude_playlists
        self.use_cache = use_cache
        SpotifyResponse.api = api

        playlists_data = self._get_playlists_data()
        tracks_data = self._get_tracks_data(playlists_data=playlists_data)

        self._logger.info(f"\33[1;95m ->\33[1;97m Processing Spotify data for "
                          f"{len(tracks_data)} tracks and {len(playlists_data)} playlists\33[0m")
        self.tracks = self._get_tracks(tracks_data=tracks_data)
        self.playlists = self._get_playlists(playlists_data=playlists_data)
        print()

    def _get_playlists_data(self) -> List[MutableMapping[str, Any]]:
        """Get playlists and all their tracks"""
        playlists_data = self.api.get_collections_user(kind=ItemType.PLAYLIST, expand=False, limit=self.limit,
                                                       use_cache=self.use_cache)
        if self.include_playlists:
            include = [name.lower() for name in self.include_playlists]
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() in include]

        if self.exclude_playlists:
            exclude = [name.lower() for name in self.exclude_playlists]
            playlists_data = [pl for pl in playlists_data if pl["name"].lower() not in exclude]

        total_tracks = sum(pl["tracks"]["total"] for pl in playlists_data)
        total_pl = len(playlists_data)
        self._logger.info(f"\33[1;95m ->\33[1;97m "
                          f"Getting {total_tracks} Spotify tracks from {total_pl} playlists\33[0m")

        self.api.get_collections(playlists_data, kind=ItemType.PLAYLIST, limit=self.limit, use_cache=self.use_cache)
        print()

        return playlists_data

    def _get_playlists(self, playlists_data: List[MutableMapping[str, Any]]) -> MutableMapping[str, SpotifyTrack]:
        """Extract playlist data from API responses to Spotify objects and return map of URI to playlist"""
        tracks = self.tracks.values()
        playlists = [SpotifyPlaylist.load(pl, items=tracks, use_cache=self.use_cache) for pl in playlists_data]
        return {playlist.name: playlist for playlist in playlists}

    def _get_tracks_data(self, playlists_data: List[MutableMapping[str, Any]]) -> List[MutableMapping[str, Any]]:
        """Get a list of unique tracks with enhanced data (i.e. features, genres etc.) across all playlists"""
        playlists_tracks_data = [pl["tracks"]["items"] for pl in playlists_data]

        tracks_data = []
        tracks_seen = set()
        for track in [item["track"] for pl in playlists_tracks_data for item in pl]:
            if not track["is_local"] and track["uri"] not in tracks_seen:
                tracks_seen.add(track["uri"])
                tracks_data.append(track)

        self._logger.info(f"\33[1;95m ->\33[1;97m Getting Spotify data for {len(tracks_data)} tracks\33[0m")
        self.api.get_items(tracks_data, kind=ItemType.TRACK, limit=50, use_cache=self.use_cache)
        self.api.get_tracks_extra(tracks_data, features=True, limit=50, use_cache=self.use_cache)
        print()

        return tracks_data

    @staticmethod
    def _get_tracks(tracks_data: List[MutableMapping[str, Any]]) -> MutableMapping[str, SpotifyTrack]:
        """Extract track data from API responses to Spotify objects and return map of URI to track"""
        tracks = [SpotifyTrack(track) for track in tracks_data]
        return {track.uri: track for track in tracks}


if __name__ == "__main__":
    api = API(
        auth_args={
            "url": f"{__URL_AUTH__}/api/token",
            "data": {
                "grant_type": "authorization_code",
                "code": None,
                "client_id": os.getenv("CLIENT_ID"),
                "client_secret": os.getenv("CLIENT_SECRET"),
                "redirect_uri": "http://localhost:8080/",
            },
        },
        user_args={
            "url": f"{__URL_AUTH__}/authorize",
            "params": {
                "response_type": "code",
                "client_id": os.getenv("CLIENT_ID"),
                "scope": " ".join(
                    [
                        "playlist-modify-public",
                        "playlist-modify-private",
                        "playlist-read-collaborative",
                    ]
                ),
                "state": "syncify",
            },
        },
        refresh_args={
            "url": f"{__URL_AUTH__}/api/token",
            "data": {
                "grant_type": "refresh_token",
                "refresh_token": None,
                "client_id": os.getenv("CLIENT_ID"),
                "client_secret": os.getenv("CLIENT_SECRET"),
            },
        },
        test_args={"url": f"{__URL_API__}/me"},
        test_condition=lambda r: "href" in r and "display_name" in r,
        test_expiry=600,
        token_file_path=f"D:\\Coding\\syncify\\_data\\token_NEW.json",
        token_key_path=["access_token"],
        header_extra={"Accept": "application/json", "Content-Type": "application/json"},
    )

    tracks = [
        "https://open.spotify.com/track/3pSL8LoyWexY7vgq84baOA?si=73b831d0154743ba",
        "https://open.spotify.com/track/6g1VQsGGteeFbJm4IEn3N4?si=0dc21d8615204196",
        "https://open.spotify.com/track/3xl7PsO7Hzuig6To9FgDm6?si=82219305bab74d1c"
    ]
    albums = [
        "https://open.spotify.com/album/2smLGydiLVrqGb9mgrjr8u?si=7ea85796fdd243ca",
        "https://open.spotify.com/album/1GbtB4zTqAsyfZEsm1RZfx?si=a472c6a3758840a2",
        "https://open.spotify.com/album/2lldMBYhZgr1mY7bg3bzKb?si=5349ff57da3c45fd"
    ]
    artists = [
        "https://open.spotify.com/artist/2siHvYaxjaW5rKVRiIrMYH?si=a2b0a875474741f1",
        "https://open.spotify.com/artist/1dfeR4HaWDbWqFHLkxsg1d?si=cc1258fe90264cab",
        "https://open.spotify.com/artist/0HlxL5hisLf59ETEPM3cUA?si=f68f78f2b39c40db"
    ]
    playlists = [
        "https://open.spotify.com/playlist/3FwOvW2WNAzfz4S9cxQldZ?si=eda3cc368179440e",
        "https://open.spotify.com/playlist/49Ep7xkcdzKAkGeoieMl6r?si=9714368133bc497e",
    ]
    users = [
        "https://open.spotify.com/user/21by3byccdz2ecmnivphf2p3y?si=9f7cd38e5e394940",
        "https://open.spotify.com/user/helenasophiemac?si=525e9f3b12e342b6",
        "https://open.spotify.com/user/1122812955?si=9370cab5095048a0"
    ]

    SpotifyResponse.api = api

    lib = SpotifyLibrary(api, exclude_playlists=["easy lover"], use_cache=True)
    pl = lib.playlists["70s"]
    print(pl.tracks[0])
    exit()



    import traceback
    import sys

    pl_new = SpotifyPlaylist.load("new", use_cache=False)
    pl = SpotifyPlaylist.load("I AM THE CAPTAIN, MY NAME IS DAVE", use_cache=False)
    pl_new.tracks = pl.tracks
    try:
        print(pl_new.sync("all"))
    except Exception as ex:
        print(traceback.format_exc())
        pl_new.delete()
    exit()

    mb = MusicBee(library_folder="D:\\Music")
    print(mb)
    uris = sorted(track.uri for track in mb.tracks if track.has_uri)
    tracks = api.get_items(uris, kind=ItemType.TRACK, use_cache=True)
    api.get_tracks_extra(tracks, features=True, use_cache=True)
    spotify_tracks = [SpotifyTrack(track) for track in tracks]

    anastasic = [track for track in spotify_tracks if track.uri == 'spotify:track:77vCn7iUHH8KAOqdOe1XjY'][0]
    anastasic.response["audio_features"]["tempo"] = 60


    # playlists = [SpotifyPlaylist(pl) for pl in api.get_collections("berge cruising", kind=ItemType.PLAYLIST, limit=100)]
    pl = SpotifyPlaylist.load("berge cruising")
    anastasic_pl = [track for track in pl.tracks if track.uri == 'spotify:track:77vCn7iUHH8KAOqdOe1XjY'][0]
    print(anastasic)
    print(anastasic_pl)
    # print(SpotifyTrack.load("https://open.spotify.com/track/7LygtNjQ65PSdzVjUnHXQb?si=d951aefaf8134a49"))
    # print(json.dumps(playlists[0].response, indent=2))

    # results = [pl for pl in endpoints.get_user_collections(kind=ItemType.PLAYLIST) if pl["name"] in ["berge cruising", "70s"]]
    # results = endpoints.get_collection_items(results)
    # for pl in results:
    #     print(json.dumps(pl["items"][0], indent=2))
    #     pl["items"] = len(pl["items"])
    # print(json.dumps(results, indent=2))
