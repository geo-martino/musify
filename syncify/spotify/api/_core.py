from abc import ABCMeta
from typing import Any

from syncify.remote.api import RemoteAPI
from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.utils.helpers import limit_value


class SpotifyAPICore(RemoteAPI, metaclass=ABCMeta):

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
            kind = RemoteItemType.from_name(input("\33[1mEnter ID type: \33[0m"))[0]

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

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_self(self, update_user_data: bool = True) -> dict[str, Any]:
        """
        ``GET: /me`` - Get API response for information on current user.

        :param update_user_data: When True, update the ``_user_data`` stored in this API object.
        """
        r = self.get(url=f"{self.api_url_base}/me", use_cache=True, log_pad=71)
        if update_user_data:
            self._user_data = r
        return r

    def query(self, query: str, kind: RemoteItemType, limit: int = 10, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        ``GET: /search`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The remote item type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        if not query or len(query) > 150:  # query is too short or too long, skip
            return []

        url = f"{self.api_url_base}/search"
        params = {'q': query, "type": kind.name.casefold(), "limit": limit_value(limit)}
        r = self.get(url, params=params, use_cache=use_cache)

        if "error" in r:
            self.logger.error(f"{'ERROR':<7}: {url:<43} | Query: {query} | {r['error']}")
            return []

        return r[f"{kind.name.casefold()}s"]["items"]
