from typing import Optional

from api.request import RequestHandler
from syncify.spotify.endpoints.basic import Basic
from syncify.spotify.endpoints.collection import Collections
from syncify.spotify.endpoints.item import Items
from syncify.spotify import IDType, ItemType
from syncify.utils.logger import Logger


class Endpoints(Basic, Items, Collections):
    """
    Collection of endpoints for the Spotify API.

    :param handler: An initialised request handler for handling API calls.
    """
    @property
    def requests(self) -> RequestHandler:
        return self._requests

    @property
    def user_id(self) -> Optional[str]:
        return self._user_id

    def __init__(self, handler: RequestHandler):
        Logger.__init__(self)
        self._requests = handler

        try:
            self._user_id: Optional[str] = self.get_self()["id"]
        except Exception:
            self._user_id = None

    ###########################################################################
    ## Misc endpoints
    ###########################################################################
    def pretty_print_uris(self, value: Optional[str] = None) -> None:
        """
        Diagnostic function. Print tracks from a given link in ``<track> - <title> | <URI> - <URL>`` format
        for a given URL/URI/ID.

        :param value: URL/URI/ID to print information for.
        """
        if not value:  # get user to paste in URL/URI
            value = input("\33[1mEnter URL/URI/ID: \33[0m")

        kind = self.get_item_type(value)
        while kind is None:
            kind = ItemType.from_name(input("\33[1mEnter ID type: \33[0m"))

        url = self.convert(value, kind=kind, type_out=IDType.URL_API)
        self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}}")
        name = self.requests.get(url)['name']

        r = {'next': f"{url}/tracks"}
        i = 0
        while r['next']:
            url = r['next']
            self._logger.debug(f"{'GET':<7}: {url:<{self.url_log_width}}")
            r = self.requests.get(url, params={'limit': 20})

            if r["offset"] == 0:
                url_open = self.convert(url, type_in=IDType.URL_OPEN, type_out=IDType.URL_OPEN)
                print(f"\n\t\33[96mShowing tracks for {kind.name.lower()}: {name} - {url_open}\33[0m\n")
                pass

            if 'error' in r:
                self._logger.warning(f"{'ERROR':<7}: {url:<{self.url_log_width}}")
                return

            tracks = [item['track'] if kind == ItemType.PLAYLIST else item for item in r["items"]]
            for i, track in enumerate(tracks, i + 1):
                print(f"\t\33[92m{str(i).zfill(len(str(r['total'])))}\33[0m - "
                      f"\33[97m{self._truncate_align_str(track['name'], 50)}\33[0m | "
                      f"\33[93m{track['uri']}\33[0m - "
                      f"{self.convert(track['uri'], type_in=IDType.URI, type_out=IDType.URL_OPEN)}")
            print()


if __name__ == "__main__":
    import json
    import os
    from syncify.spotify import __URL_AUTH__, __URL_API__

    handler = RequestHandler(
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

    endpoints = Endpoints(handler=handler)
    tracks = [
        "https://open.spotify.com/track/3pSL8LoyWexY7vgq84baOA?si=73b831d0154746ba",
        "https://open.spotify.com/track/6g1VQsGGteeFbJm4IEn3N4?si=0dc21d8615204196",
        "https://open.spotify.com/track/3xl7PsO7Hzuig6To9FgDm6?si=82219305bab74d1c"
    ]
    albums = [
        "https://open.spotify.com/album/2smLGydiLVrqGb9mgrjr8u?si=7ea85796fdd246ca",
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

    endpoints.create_playlist("new")
    endpoints.delete_playlist("new")
    #endpoints.clear_from_playlist("70s", items=["https://open.spotify.com/track/3pSL8LoyWexY7vgq84baOA?si=73b831d0154746ba"])

    # print(endpoints.get_playlist_url("70s"))
    # #print(json.dumps(endpoints.get_audio_features(tracks), indent=2))
    #
    # results = [pl for pl in endpoints.get_user_collections(kind=ItemType.PLAYLIST) if pl["name"] in ["berge cruising", "70s"]]
    # results = endpoints.get_collection_items(results)
    # for pl in results:
    #     print(json.dumps(pl["items"][0], indent=2))
    #     pl["items"] = len(pl["items"])
    # print(json.dumps(results, indent=2))
