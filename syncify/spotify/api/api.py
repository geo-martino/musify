from syncify.remote.api.api import RemoteAPI
from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.spotify.api.collection import SpotifyAPICollections
from syncify.spotify.api.core import SpotifyAPICore
from syncify.spotify.api.item import SpotifyAPIItems
from syncify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyAPI(RemoteAPI, SpotifyAPICore, SpotifyAPIItems, SpotifyAPICollections, SpotifyDataWrangler):
    """
    Collection of endpoints for a remote API.
    See :py:class:`RequestHandler` and :py:class:`APIAuthoriser`
    for more info on which params to pass to authorise and execute requests.

    :param handler_kwargs: The authorisation kwargs to be passed to :py:class:`RequestHandler`.
    """

    def __init__(self, **handler_kwargs):
        RemoteAPI.__init__(self, name=self.remote_source, **handler_kwargs)

        try:
            user_data = self.get_self()
            self._user_id: str | None = user_data["id"]
            self._user_name: str | None = user_data["display_name"]
        except (ConnectionError, KeyError, TypeError):
            pass

    def pretty_print_uris(
            self, value: str | None = None, kind: RemoteIDType | None = None, use_cache: bool = True
    ) -> None:
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
            kind = self.get_item_type(value)

        while kind is None:  # get user to input ID type
            kind = RemoteItemType.from_name(input("\33[1mEnter ID type: \33[0m"))

        url = self.convert(value, kind=kind, type_out=RemoteIDType.URL)
        name = self.get(url, log_pad=43)["name"]

        r = {"next": f"{url}/tracks"}
        i = 0
        while r["next"]:  # loop through each page, printing data in blocks of 20
            url = r["next"]
            r = self.get(url, params={"limit": 20}, use_cache=use_cache)

            if r["offset"] == 0:  # first page, show header
                url_open = self.convert(url, type_in=RemoteIDType.URL_EXT, type_out=RemoteIDType.URL_EXT)
                print(
                    f"\n\t\33[96mShowing tracks for {kind.name.casefold()}\33[0m: "
                    f"\33[94m{name} \33[97m- {url_open} \33[0m\n"
                )
                pass

            if "error" in r:  # fail
                self.logger.warning(f"{"ERROR":<7}: {url:<43}")
                return

            tracks = [item["track"] if kind == RemoteItemType.PLAYLIST else item for item in r["items"]]
            for i, track in enumerate(tracks, i + 1):  # print each item in this page
                formatted_item_data = self.format_item_data(
                    i=i, name=track["name"], uri=track["uri"], length=track["duration_ms"] / 1000, total=r["total"]
                )
                print(formatted_item_data)
            print()
