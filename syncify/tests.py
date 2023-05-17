import os

from syncify.abstract.collection import BasicCollection
from syncify.spotify.library import SpotifyPlaylist
from syncify.spotify.processor import Searcher, Checker
from syncify.local.library import MusicBee
from syncify.spotify import __URL_AUTH__, __URL_API__
from syncify.spotify.api import API
from syncify.spotify.library import SpotifyLibrary
from syncify.spotify.library.item import SpotifyResponse

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

    mb = MusicBee(library_folder="D:\\Music", exclude=["B A S S"])
    print(mb)

    lib = SpotifyLibrary(api, exclude=["easy lover"], use_cache=True)
    pl = lib.playlists["70s"]

    SpotifyResponse.api = api
    pl = SpotifyPlaylist.load("I AM THE CAPTAIN, MY NAME IS DAVE")
    for track in pl:
        track.uri = None
        track.has_uri = None

    searcher = Searcher(api=api)
    results = searcher.search([pl])
    checker = Checker(api=api)
    checker.check([BasicCollection("test", list(results.values())[0].matched)])

    import traceback

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
