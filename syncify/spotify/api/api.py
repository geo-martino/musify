from typing import Optional

from syncify.spotify.api.request import RequestHandler
from syncify.spotify.api.basic import Basic
from syncify.spotify.api.collection import Collections
from syncify.spotify.api.item import Items
from syncify.spotify import IDType, ItemType, __URL_AUTH__, __URL_API__
from syncify.utils.logger import Logger

AUTH_ARGS_BASIC = {
    "auth_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "client_credentials",
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "user_args": None,
    "refresh_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}

AUTH_ARGS_USER = {
    "auth_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "authorization_code",
            "code": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
            "redirect_uri": "http://localhost:8080/",
        },
    },
    "user_args": {
        "url": f"{__URL_AUTH__}/authorize",
        "params": {
            "response_type": "code",
            "client_id": "{client_id}",
            "scope": " ".join(
                [
                    "playlist-modify-public",
                    "playlist-modify-private",
                    "playlist-read-collaborative",
                ]
            ),
            "redirect_uri": "http://localhost:8080/",
            "state": "syncify",
        },
    },
    "refresh_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_args": {"url": f"{__URL_API__}/me"},
    "test_condition": lambda r: "href" in r and "display_name" in r,
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}


class API(Basic, Items, Collections):
    """
    Collection of endpoints for the Spotify API.
    See :py:class:`RequestHandler` and :py:class:`APIAuthoriser`
    for more info on which params to pass to authorise and execute requests.

    :param handler_kwargs: The authorisation kwargs to be passed to :py:class:`RequestHandler`.
    """
    @property
    def user_id(self) -> Optional[str]:
        return self._user_id

    def __init__(self, **handler_kwargs):
        Logger.__init__(self)
        RequestHandler.__init__(self, **handler_kwargs)

        try:
            user_data = self.get_self()
            self._user_id: Optional[str] = user_data["id"]
            self.user_name: Optional[str] = user_data["display_name"]
        except (ConnectionError, KeyError, TypeError):
            self._user_id = None
            self.user_name = None

    ###########################################################################
    ## Misc endpoints
    ###########################################################################
    def format_item_data(self, i: int, name: str, uri: str, total: int, max_width=50) -> str:
        """
        Pretty format item data for displaying to the user

        :param i: The position of this item in the collection.
        :param name: The name of the item.
        :param uri: The URI of the item.
        :param total: The total number of items in the collection
        :param max_width: The maximum width to print names as. Any name lengths longer than this will be truncated.
        """
        return f"\t\33[92m{str(i).zfill(len(str(total)))} \33[0m- "\
               f"\33[97m{self.truncate_align_str(name, max_width=max_width)} \33[0m| "\
               f"\33[93m{uri} \33[0m- "\
               f"{self.convert(uri, type_in=IDType.URI, type_out=IDType.URL_EXT)}"

    def pretty_print_uris(self, value: Optional[str] = None, kind: Optional[IDType] = None, use_cache: bool = True):
        """
        Diagnostic function. Print tracks from a given link in ``<track> - <title> | <URI> - <URL>`` format
        for a given URL/URI/ID.

        :param value: URL/URI/ID to print information for.
        :param kind: When an ID is provided, give the kind of ID this is here.
            If None and ID is given, user will be prompted to give the kind anyway.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        if not value:  # get user to paste in URL/URI
            value = input("\33[1mEnter URL/URI/ID: \33[0m")
        if not kind:
            kind = self._get_item_type(value)

        while kind is None:
            kind = ItemType.from_name(input("\33[1mEnter ID type: \33[0m"))

        url = self.convert(value, kind=kind, type_out=IDType.URL)
        name = self.get(url, log_pad=43)['name']

        r = {'next': f"{url}/tracks"}
        i = 0
        while r['next']:
            url = r['next']
            r = self.get(url, params={'limit': 20}, use_cache=use_cache)

            if r["offset"] == 0:
                url_open = self.convert(url, type_in=IDType.URL_EXT, type_out=IDType.URL_EXT)
                print(f"\n\t\33[96mShowing tracks for {kind.name.casefold()}: {name} - {url_open} \33[0m\n")
                pass

            if 'error' in r:
                self.logger.warning(f"{'ERROR':<7}: {url:<43}")
                return

            tracks = [item['track'] if kind == ItemType.PLAYLIST else item for item in r["items"]]
            for i, track in enumerate(tracks, i + 1):
                print(self.format_item_data(i=i, name=track['name'], uri=track['uri'], total=r['total'], max_width=50))
            print()
