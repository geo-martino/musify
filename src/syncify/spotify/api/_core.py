from abc import ABCMeta
from collections.abc import MutableMapping
from typing import Any

from syncify.remote.enums import RemoteIDType, RemoteObjectType
from syncify.spotify.api._base import SpotifyAPIBase
from syncify.utils.helpers import limit_value


class SpotifyAPICore(SpotifyAPIBase, metaclass=ABCMeta):

    def print_collection(
            self,
            value: str | MutableMapping[str, Any] | None = None,
            kind: RemoteIDType | None = None,
            limit: int = 20,
            use_cache: bool = True
    ) -> None:
        """
        Diagnostic function.
        Print items from a given collection in ``<track> - <title> | <URI> - <URL>`` format for a given URL/URI/ID.

        ``value`` may be:
            * A string representing a URL/URI/ID.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.

        :param value: The value representing some remote collection. See description for allowed value types.
        :param kind: When an ID is provided, give the kind of ID this is here.
            If None and ID is given, user will be prompted to give the kind anyway.
        :param limit: The number of results to call per request and,
            therefore, the number of items in each printed block.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        if not value:  # get user to paste in URL/URI
            value = input("\33[1mEnter URL/URI/ID: \33[0m")
        if not kind:
            kind = self.get_item_type(value)
        key = self.collection_item_map[kind].name.casefold()

        while kind is None:  # get user to input ID type
            kind = RemoteObjectType.from_name(input("\33[1mEnter ID type: \33[0m"))[0]

        id_ = self.extract_ids(values=value, kind=kind)[0]
        url = self.convert(id_, kind=kind, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        limit = limit_value(limit, floor=1, ceil=50)

        name = self.get(url, params={"limit": limit}, log_pad=43)["name"]
        response = self.get(f"{url}/{key}s", params={"limit": limit}, log_pad=43)

        i = 0
        while response.get("next") or i < response["total"]:  # loop through each page, printing data in blocks of 20
            if response.get("offset", 0) == 0:  # first page, show header
                url_ext = self.convert(id_, kind=kind, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL_EXT)
                print(
                    f"\n\t\33[96mShowing tracks for {kind.name.casefold()}\33[0m: "
                    f"\33[94m{name} \33[97m- {url_ext} \33[0m\n"
                )

            tracks = [item[key] if key in item else item for item in response[self.items_key]]
            for i, track in enumerate(tracks, i + 1):  # print each item in this page
                length = track["duration_ms"] / 1000
                self.print_item(i=i, name=track["name"], uri=track["uri"], length=length, total=response["total"])

            if response["next"]:
                response = self.get(response["next"], params={"limit": limit}, use_cache=use_cache)
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

    def query(
            self, query: str | None, kind: RemoteObjectType, limit: int = 10, use_cache: bool = True
    ) -> list[dict[str, Any]]:
        """
        ``GET: /search`` - Query for items. Modify result types returned with kind parameter

        :param query: Search query.
        :param kind: The remote object type to search for.
        :param limit: Number of results to get and return.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The response from the endpoint.
        """
        if not query or len(query) > 150:  # query is too short or too long, skip
            return []

        url = f"{self.api_url_base}/search"
        params = {'q': query, "type": kind.name.casefold(), "limit": limit_value(limit, floor=1, ceil=50)}
        r = self.get(url, params=params, use_cache=use_cache)

        if "error" in r:
            self.logger.error(f"{'ERROR':<7}: {url:<43} | Query: {query} | {r['error']}")
            return []

        return r[f"{kind.name.casefold()}s"]["items"]
