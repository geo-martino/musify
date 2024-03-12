"""
Implements endpoints for manipulating playlists with the Spotify API.
"""

from abc import ABCMeta
from collections.abc import Collection, Mapping
from itertools import batched
from typing import Any

from musify import PROGRAM_NAME, PROGRAM_URL
from musify.shared.remote.enum import RemoteIDType, RemoteObjectType
from musify.shared.remote.exception import RemoteIDTypeError
from musify.shared.utils import limit_value
from musify.spotify.api.base import SpotifyAPIBase


class SpotifyAPIPlaylists(SpotifyAPIBase, metaclass=ABCMeta):
    """API endpoints for processing collections i.e. playlists, albums, shows, and audiobooks"""

    def get_playlist_url(self, playlist: str | Mapping[str, Any], use_cache: bool = True) -> str:
        """
        Determine the type of the given ``playlist`` and return its API URL.
        If type cannot be determined, attempt to find the playlist in the
        list of the currently authorised user's playlists.

        :param playlist: One of the following to identify the playlist URL:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :return: The playlist URL.
        :raise RemoteIDTypeError: Raised when the function cannot determine the item type of
            the input ``playlist``. Or when it does not recognise the type of the input ``playlist`` parameter.
        """
        if isinstance(playlist, Mapping):
            if "href" in playlist:
                return playlist["href"]
            elif "id" in playlist:
                return self.convert(
                    playlist["id"], kind=RemoteObjectType.PLAYLIST, type_in=RemoteIDType.ID, type_out=RemoteIDType.URL
                )
            elif "uri" in playlist:
                return self.convert(
                    playlist["uri"], kind=RemoteObjectType.PLAYLIST, type_in=RemoteIDType.URI, type_out=RemoteIDType.URL
                )
        try:
            return self.convert(playlist, kind=RemoteObjectType.PLAYLIST, type_out=RemoteIDType.URL)
        except RemoteIDTypeError:
            playlists = self.get_user_items(kind=RemoteObjectType.PLAYLIST, use_cache=use_cache)
            playlists = {pl["name"]: pl["href"] for pl in playlists}
            if playlist not in playlists:
                raise RemoteIDTypeError(
                    "Given playlist is not a valid URL/URI/ID and name not found in user's playlists",
                    value=playlist
                )
            return playlists[playlist]

    ###########################################################################
    ## POST endpoints
    ###########################################################################
    def create_playlist(self, name: str, public: bool = True, collaborative: bool = False, *_, **__) -> str:
        """
        ``POST: /users/{user_id}/playlists`` - Create an empty playlist for the current user with the given name.

        :param name: Name of playlist to create.
        :param public: Set playlist availability as `public` if True and `private` if False.
        :param collaborative: Set playlist to collaborative i.e. other users may edit the playlist.
        :return: API URL for playlist.
        """
        url = f"{self.api_url_base}/users/{self.user_id}/playlists"

        body = {
            "name": name,
            "description": f"Generated using {PROGRAM_NAME}: {PROGRAM_URL}",
            "public": public,
            "collaborative": collaborative,
        }
        pl_url = self.handler.post(url, json=body, log_pad=71)["href"]

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Created playlist: '{name}' -> {pl_url}")
        return pl_url

    def add_to_playlist(
            self, playlist: str | Mapping[str, Any], items: Collection[str], limit: int = 100, skip_dupes: bool = True
    ) -> int:
        """
        ``POST: /playlists/{playlist_id}/tracks`` - Add list of tracks to a given playlist.

        :param playlist: One of the following to identify the playlist to clear:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
        :param items: List of URLs/URIs/IDs of the tracks to add.
        :param limit: Size of each batch of IDs to add. This value will be limited to be between ``1`` and ``100``.
        :param skip_dupes: Skip duplicates.
        :return: The number of tracks added to the playlist.
        :raise RemoteIDTypeError: Raised when the input ``playlist`` does not represent
            a playlist URL/URI/ID.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``items``
            are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"

        if len(items) == 0:
            self.logger.debug(f"{'SKIP':<7}: {url:<43} | No data given")
            return 0

        self.validate_item_type(items, kind=RemoteObjectType.TRACK)

        uri_list = [self.convert(item, kind=RemoteObjectType.TRACK, type_out=RemoteIDType.URI) for item in items]
        if skip_dupes:  # skip tracks currently in playlist
            pl_current = self.get_items(url, kind=RemoteObjectType.PLAYLIST, use_cache=False)[0]
            tracks_key = self.collection_item_map[RemoteObjectType.PLAYLIST].name.lower() + "s"
            tracks = pl_current[tracks_key][self.items_key]

            uri_current = [track["track"]["uri"] for track in tracks]
            uri_list = [uri for uri in uri_list if uri not in uri_current]

        limit = limit_value(limit, floor=1, ceil=100)
        for uris in batched(uri_list, limit):  # add tracks in batches
            log = [f"Adding {len(uris):>6} items"]
            self.handler.post(url, json={"uris": uris}, log_pad=71, log_extra=log)

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Added {len(uri_list):>6} items to playlist: {url}")
        return len(uri_list)

    ###########################################################################
    ## DELETE endpoints
    ###########################################################################
    def delete_playlist(self, playlist: str | Mapping[str, Any]) -> str:
        """
        ``DELETE: /playlists/{playlist_id}/followers`` - Unfollow a given playlist.
        WARNING: This function will destructively modify your remote playlists.

        :param playlist: Playlist URL/URI/ID to unfollow OR the name of the playlist in the current user's playlists.
        :return: API URL for playlist.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/followers"
        self.handler.delete(url, log_pad=43)
        return url

    def clear_from_playlist(
            self, playlist: str | Mapping[str, Any], items: Collection[str] | None = None, limit: int = 100
    ) -> int:
        """
        ``DELETE: /playlists/{playlist_id}/tracks`` - Clear tracks from a given playlist.
        WARNING: This function can destructively modify your remote playlists.

        :param playlist: One of the following to identify the playlist to clear:
            - playlist URL/URI/ID,
            - the name of the playlist in the current user's playlists,
            - the API response of a playlist.
        :param items: List of URLs/URIs/IDs of the tracks to remove. If None, clear all songs from the playlist.
        :param limit: Size of each batch of IDs to clear in a single request.
            This value will be limited to be between ``1`` and ``100``.
        :return: The number of tracks cleared from the playlist.
        :raise RemoteIDTypeError: Raised when the input ``playlist`` does not represent
            a playlist URL/URI/ID.
        :raise RemoteObjectTypeError: Raised when the item types of the input ``items``
            are not all tracks or IDs.
        """
        url = f"{self.get_playlist_url(playlist, use_cache=False)}/tracks"
        if items is not None and len(items) == 0:
            self.logger.debug(f"{'SKIP':<7}: {url:<43} | No data given")
            return 0

        if items is None:  # clear everything
            pl_current = self.get_items(url, kind=RemoteObjectType.PLAYLIST, extend=True, use_cache=False)[0]

            tracks_key = self.collection_item_map[RemoteObjectType.PLAYLIST].name.lower() + "s"
            tracks = pl_current[tracks_key][self.items_key]
            uri_list = [track[tracks_key.rstrip("s")]["uri"] for track in tracks]
        else:  # clear only the items given
            self.validate_item_type(items, kind=RemoteObjectType.TRACK)
            uri_list = [self.convert(item, kind=RemoteObjectType.TRACK, type_out=RemoteIDType.URI) for item in items]

        if not uri_list:  # skip when nothing to clear
            self.logger.debug(f"{'SKIP':<7}: {url:<43} | No tracks to clear")
            return 0

        limit = limit_value(limit, floor=1, ceil=100)
        for uris in batched(uri_list, limit):  # clear in batches
            body = {"tracks": [{"uri": uri} for uri in uris]}
            log = [f"Clearing {len(uri_list):>3} tracks"]
            self.handler.delete(url, json=body, log_pad=71, log_extra=log)

        self.logger.debug(f"{'DONE':<7}: {url:<71} | Cleared {len(uri_list):>3} tracks")
        return len(uri_list)
