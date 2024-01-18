"""
Implements all required non-items and non-playlist endpoints from the Spotify API.
"""

from abc import ABCMeta
from collections.abc import MutableMapping
from typing import Any

from musify.shared.remote.enum import RemoteIDType, RemoteObjectType
from musify.shared.types import Number
from musify.shared.utils import limit_value
from musify.spotify.api.base import SpotifyAPIBase


class SpotifyAPIMisc(SpotifyAPIBase, metaclass=ABCMeta):

    def print_collection(
            self,
            value: str | MutableMapping[str, Any] | None = None,
            kind: RemoteIDType | None = None,
            limit: int = 20,
            use_cache: bool = True
    ) -> None:
        if not value:  # get user to paste in URL/URI
            value = input("\33[1mEnter URL/URI/ID: \33[0m")
        if not kind:
            kind = self.get_item_type(value)
        key = self.collection_item_map[kind].name.lower()

        while kind is None:  # get user to input ID type
            kind = RemoteObjectType.from_name(input("\33[1mEnter ID type: \33[0m"))[0]

        id_ = self.extract_ids(values=value, kind=kind)[0]
        url = self.convert(id_, kind=kind, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL)
        limit = limit_value(limit, floor=1, ceil=50)

        name = self.handler.get(url, params={"limit": limit}, log_pad=43)["name"]
        response = self.handler.get(f"{url}/{key}s", params={"limit": limit}, log_pad=43)

        i = 0
        while response.get("next") or i < response["total"]:  # loop through each page, printing data in blocks of 20
            if response.get("offset", 0) == 0:  # first page, show header
                url_ext = self.convert(id_, kind=kind, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL_EXT)
                print(
                    f"\n\t\33[96mShowing tracks for {kind.name.lower()}\33[0m: "
                    f"\33[94m{name} \33[97m- {url_ext} \33[0m\n"
                )

            tracks = [item[key] if key in item else item for item in response[self.items_key]]
            for i, track in enumerate(tracks, i + 1):  # print each item in this page
                if isinstance(track["duration_ms"], Number):
                    length = track["duration_ms"] / 1000
                else:
                    length = track["duration_ms"]["totalMilliseconds"] / 1000
                self.print_item(i=i, name=track["name"], uri=track["uri"], length=length, total=response["total"])

            if response["next"]:
                response = self.handler.get(response["next"], params={"limit": limit}, use_cache=use_cache)
            print()

    ###########################################################################
    ## GET endpoints
    ###########################################################################
    def get_self(self, update_user_data: bool = True) -> dict[str, Any]:
        """
        ``GET: /me`` - Get API response for information on current user.

        :param update_user_data: When True, update the ``_user_data`` stored in this API object.
        """
        r = self.handler.get(url=f"{self.api_url_base}/me", use_cache=True, log_pad=71)
        if update_user_data:
            self.user_data = r
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
        params = {'q': query, "type": kind.name.lower(), "limit": limit_value(limit, floor=1, ceil=50)}
        response = self.handler.get(url, params=params, use_cache=use_cache)

        if "error" in response:
            self.logger.error(f"{'ERROR':<7}: {url:<43} | Query: {query} | {response['error']}")
            return []

        results = response[f"{kind.name.lower()}s"]["items"]
        if kind not in self.collection_item_map:
            return results

        key = self.collection_item_map[kind].name.lower() + "s"
        totals_key = {
            RemoteObjectType.ALBUM: "total_tracks",
            RemoteObjectType.SHOW: "total_episodes",
            RemoteObjectType.AUDIOBOOK: "total_chapters"
        }
        for result in results:
            if key in result and "href" in result[key] and "total" in result[key]:
                continue

            href = self.format_next_url(f"{result["href"]}/{key}", limit=50)
            result[key] = {"href": href, "total": result.get(totals_key.get(kind), 0)}

        return results
